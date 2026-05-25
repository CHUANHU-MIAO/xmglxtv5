import hashlib
import json
import os
import platform
import subprocess
import uuid

import requests

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')


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


class SubscriptionClient:
    def __init__(self, server_url=None):
        self.server_url = server_url or 'http://127.0.0.1:5001'
        self.token = None
        self.user_info = None
        self._load_config()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                self.server_url = cfg.get('server_url', self.server_url)
                self.token = cfg.get('token')
                self.user_info = cfg.get('user_info')
            except Exception:
                pass

    def save_config(self):
        cfg = {
            'server_url': self.server_url,
            'token': self.token,
            'user_info': self.user_info,
        }
        data_root = os.environ.get('DATA_ROOT', '')
        if data_root:
            cfg['data_root'] = data_root
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_data_root(self, data_root):
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                pass
        cfg['data_root'] = data_root
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def save_credentials(self, username, password, remember_password=False):
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                pass
        if remember_password:
            cfg['saved_username'] = username
            cfg['saved_password'] = password
            cfg['remember_password'] = True
        else:
            cfg['saved_username'] = username
            cfg['saved_password'] = ''
            cfg['remember_password'] = False
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_saved_credentials(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                username = cfg.get('saved_username', '')
                password = cfg.get('saved_password', '') if cfg.get('remember_password') else ''
                remember = cfg.get('remember_password', False)
                return username, password, remember
            except Exception:
                pass
        return '', '', False

    def login(self, username, password):
        device_id = get_machine_fingerprint()
        device_name = platform.node()
        try:
            resp = requests.post(
                f'{self.server_url}/api/auth/login',
                json={
                    'username': username,
                    'password': password,
                    'device_id': device_id,
                    'device_name': device_name,
                },
                timeout=10,
            )
            data = resp.json()
            if data.get('success') and data.get('token'):
                self.token = data['token']
                self.user_info = data.get('user')
                self.save_config()
                return True, '登录成功'
            return False, data.get('message', '登录失败')
        except requests.exceptions.ConnectionError:
            return False, f'无法连接服务器（{self.server_url}）'
        except Exception as e:
            return False, f'登录时发生错误：{str(e)}'

    def verify(self):
        if not self.token:
            return False, '未登录'
        try:
            resp = requests.post(
                f'{self.server_url}/api/auth/verify',
                json={'token': self.token},
                timeout=10,
            )
            data = resp.json()
            if data.get('valid'):
                self.user_info = data.get('user')
                return True, '验证通过'
            self.token = None
            self.user_info = None
            self.save_config()
            return False, 'Token已失效'
        except requests.exceptions.ConnectionError:
            return False, f'无法连接服务器（{self.server_url}）'
        except Exception as e:
            return False, f'验证时发生错误：{str(e)}'

    def logout(self):
        if self.token:
            try:
                requests.post(
                    f'{self.server_url}/api/auth/logout',
                    json={'token': self.token},
                    timeout=5,
                )
            except Exception:
                pass
        self.token = None
        self.user_info = None
        self.save_config()

    def create_pair(self):
        device_id = get_machine_fingerprint()
        try:
            resp = requests.post(
                f'{self.server_url}/api/pair/create',
                json={'device_fingerprint': device_id},
                timeout=10,
            )
            data = resp.json()
            if data.get('success'):
                return data
            return None
        except Exception:
            return None

    def poll_pair_status(self, code):
        try:
            resp = requests.get(
                f'{self.server_url}/api/pair/status',
                params={'code': code},
                timeout=10,
            )
            data = resp.json()
            if data.get('success') and data.get('status') == 'confirmed' and data.get('token'):
                self.token = data['token']
                self.user_info = data.get('user')
                self.save_config()
                return True, '配对成功'
            return False, data.get('message', '等待扫码...')
        except requests.exceptions.ConnectionError:
            return False, f'无法连接服务器（{self.server_url}）'
        except Exception as e:
            return False, f'配对时发生错误：{str(e)}'