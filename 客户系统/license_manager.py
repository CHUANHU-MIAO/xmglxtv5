import hashlib
import json
import os
import sys
import uuid
import platform
import subprocess
from datetime import datetime

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

LICENSE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'license.key')

PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3OQsHVdzZY+tX0YEnQXV
GoUTMt/7IOvmXI8j01a8lHsKRCnaA5nglJTNoRDdYtRUq+EsFN0Ne7L7TfudztGj
EwnTobeFrhfdpeKWA2wM70ym3b6TdXwi0FaQF+bP6SCr7VradvNZqlqoPkNjhnVr
WWwJsgNL8VbXsX8dOdwX/GigHEbYR5Pm8nOOnHr0ccgufBHHlBQn8u0fUKYEvRmP
8O7MpUerXTXj20lVgPvlVCO5TN3pxgidtw3AVVUz1HcpYoshFbxRqu365ADgyjat
3g8EpdxG9VgnHFHUxFAngxPdvJJSZRyAWbPtp8xRARnIDS6ngb2nmZfwyIizEjNm
BwIDAQAB
-----END PUBLIC KEY-----"""


def get_mac_address():
    mac = uuid.getnode()
    return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(40, -1, -8))


def get_disk_serial():
    current_os = platform.system()
    if current_os == 'Windows':
        try:
            result = subprocess.run(
                ['wmic', 'diskdrive', 'get', 'serialnumber'],
                capture_output=True, text=True, timeout=5
            )
            lines = [l.strip() for l in result.stdout.strip().split('\n')
                     if l.strip() and l.strip() != 'SerialNumber']
            return lines[0] if lines else 'UNKNOWN_DISK'
        except Exception:
            return 'UNKNOWN_DISK'
    else:
        for lsblk_path in ('/usr/bin/lsblk', '/usr/sbin/lsblk', 'lsblk'):
            try:
                result = subprocess.run(
                    [lsblk_path, '-o', 'SERIAL', '-nd'],
                    capture_output=True, text=True, timeout=5
                )
                serials = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                return serials[0] if serials else 'UNKNOWN_DISK'
            except Exception:
                continue
        return 'UNKNOWN_DISK'


def get_cpu_id():
    current_os = platform.system()
    if current_os == 'Windows':
        try:
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'ProcessorId'],
                capture_output=True, text=True, timeout=5
            )
            lines = [l.strip() for l in result.stdout.strip().split('\n')
                     if l.strip() and l.strip() != 'ProcessorId']
            return lines[0] if lines else 'UNKNOWN_CPU'
        except Exception:
            return 'UNKNOWN_CPU'
    else:
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'Serial' in line:
                        val = line.split(':')[1].strip()
                        if val:
                            return val
        except Exception:
            pass
        for dmidecode_path in ('/usr/sbin/dmidecode', '/usr/bin/dmidecode', 'dmidecode'):
            try:
                result = subprocess.run(
                    [dmidecode_path, '-t', 'processor'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'ID:' in line:
                        val = line.split(':')[1].strip()
                        if val:
                            return val
            except Exception:
                continue
        return 'UNKNOWN_CPU'


def get_machine_fingerprint():
    mac = get_mac_address()
    disk = get_disk_serial()
    cpu = get_cpu_id()
    raw = f"{mac}|{disk}|{cpu}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_machine_info():
    return {
        'mac': get_mac_address(),
        'disk': get_disk_serial(),
        'cpu': get_cpu_id(),
        'fingerprint': get_machine_fingerprint(),
        'hostname': platform.node(),
        'os': platform.system() + ' ' + platform.release()
    }


def verify_license():
    if not CRYPTO_AVAILABLE:
        return False, '加密库未安装，请执行: pip install cryptography'

    if not os.path.exists(LICENSE_FILE):
        return False, '系统未激活，请联系管理员获取授权文件。'

    try:
        with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
            license_data = json.load(f)

        required = ['fingerprint', 'product', 'signature']
        if not all(field in license_data for field in required):
            return False, '授权文件格式无效。'

        if license_data['product'] != 'xinAo_project_system':
            return False, '授权文件产品不匹配。'

        current_fp = get_machine_fingerprint()
        if license_data['fingerprint'] != current_fp:
            return False, '授权文件与当前设备不匹配，请联系管理员重新授权。'

        message = f"{license_data['fingerprint']}|xinAo_project_system"
        signature = bytes.fromhex(license_data['signature'])

        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
        public_key.verify(
            signature,
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return True, '授权永久有效（买断制）'

    except Exception:
        return False, '授权验证失败，签名无效或文件被篡改。'


def check_license_or_exit():
    valid, message = verify_license()
    if not valid:
        print(f'\n{"="*60}')
        print(f'  授权验证失败')
        print(f'  {message}')
        print(f'{"="*60}')
        print(f'\n本机设备信息（用于申请授权）：')
        info = get_machine_info()
        print(f'  设备指纹: {info["fingerprint"]}')
        print(f'  计算机名: {info["hostname"]}')
        print(f'  MAC地址:  {info["mac"]}')
        print(f'  CPU序列号: {info["cpu"]}')
        print(f'  磁盘序列号: {info["disk"]}')
        print(f'\n请联系管理员获取授权文件后，将 license.key 放入程序目录。')
        print(f'{"="*60}\n')
        sys.exit(1)
    else:
        print(f'{message}')