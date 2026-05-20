import hashlib
import json
import os
import sys
from datetime import datetime, timedelta

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_FILE = os.path.join(SCRIPT_DIR, 'private_key.pem')
PUBLIC_KEY_FILE = os.path.join(SCRIPT_DIR, 'public_key.pem')


def generate_key_pair():
    if not CRYPTO_AVAILABLE:
        print('加密库未安装，请执行: pip install cryptography')
        return False

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open(PRIVATE_KEY_FILE, 'wb') as f:
        f.write(private_pem)

    with open(PUBLIC_KEY_FILE, 'wb') as f:
        f.write(public_pem)

    print(f'密钥对已生成')
    print(f'   私钥文件: {PRIVATE_KEY_FILE}')
    print(f'   公钥文件: {PUBLIC_KEY_FILE}')
    print(f'请将公钥内容复制到客户端的 license_manager.py 中')
    return True


def load_private_key():
    if not os.path.exists(PRIVATE_KEY_FILE):
        print(f'私钥文件不存在: {PRIVATE_KEY_FILE}')
        print(f'请先运行: python license_generator.py --generate-keys')
        return None

    with open(PRIVATE_KEY_FILE, 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def generate_license(fingerprint, expire_date_str, product='xinAo_project_system'):
    private_key = load_private_key()
    if not private_key:
        return None

    message = f"{fingerprint}|{expire_date_str}|{product}"
    signature = private_key.sign(
        message.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    license_data = {
        'product': product,
        'fingerprint': fingerprint,
        'expire_date': expire_date_str,
        'issue_date': datetime.now().strftime('%Y-%m-%d'),
        'signature': signature.hex(),
        'version': '1.0'
    }
    return license_data


def auto_deploy(project_path):
    project_path = os.path.abspath(project_path)
    if not os.path.isdir(project_path):
        print(f'项目目录不存在: {project_path}')
        return

    manager_path = os.path.join(project_path, 'license_manager.py')
    if not os.path.isfile(manager_path):
        print(f'项目目录中未找到 license_manager.py: {project_path}')
        return

    sys.path.insert(0, project_path)
    try:
        from license_manager import get_machine_fingerprint, get_machine_info
    except ImportError as e:
        print(f'无法导入 license_manager 模块: {e}')
        return
    finally:
        if project_path in sys.path:
            sys.path.remove(project_path)

    print('='*60)
    print('  河北鑫奥项目管理系统 - 一键部署')
    print('='*60)

    info = get_machine_info()
    fingerprint = info['fingerprint']

    print(f'\n设备信息：')
    print(f'  计算机名:  {info["hostname"]}')
    print(f'  设备指纹:  {fingerprint}')
    print(f'  MAC地址:   {info["mac"]}')
    print(f'  CPU序列号: {info["cpu"]}')
    print(f'  磁盘序列号: {info["disk"]}')

    default_expire = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    expire_input = input(f'\n授权到期日期 [默认: {default_expire}]: ').strip()
    expire_date_str = expire_input if expire_input else default_expire

    try:
        datetime.strptime(expire_date_str, '%Y-%m-%d')
    except ValueError:
        print('日期格式错误，请使用 YYYY-MM-DD 格式')
        return

    license_data = generate_license(fingerprint, expire_date_str)
    if not license_data:
        return

    license_file = os.path.join(project_path, 'license.key')
    with open(license_file, 'w', encoding='utf-8') as f:
        json.dump(license_data, f, ensure_ascii=False, indent=2)

    days = (datetime.strptime(expire_date_str, '%Y-%m-%d') - datetime.now()).days
    print(f'\n部署完成！')
    print(f'  License文件: {license_file}')
    print(f'  到期日期:    {expire_date_str}（剩余 {days} 天）')
    print(f'  指纹:        {fingerprint}')
    print(f'\n系统启动时将自动验证授权。')
    print('='*60)


def manual_generate():
    print('\n请选择操作：')
    print('1. 生成License文件（手动输入指纹）')
    print('2. 查看公钥内容（用于部署到客户端）')
    print('3. 退出')

    choice = input('\n请输入选项 (1-3): ').strip()

    if choice == '1':
        fingerprint = input('\n请输入客户设备指纹: ').strip()
        if not fingerprint:
            print('设备指纹不能为空')
            return

        expire_date_str = input('请输入授权到期日期 (格式: 2027-05-19): ').strip()
        try:
            datetime.strptime(expire_date_str, '%Y-%m-%d')
        except ValueError:
            print('日期格式错误，请使用 YYYY-MM-DD 格式')
            return

        license_data = generate_license(fingerprint, expire_date_str)
        if license_data:
            output_file = os.path.join(SCRIPT_DIR, f'license_{fingerprint[:8]}_{expire_date_str}.key')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(license_data, f, ensure_ascii=False, indent=2)

            print(f'\nLicense 已生成')
            print(f'   设备指纹: {fingerprint}')
            print(f'   到期日期: {expire_date_str}')
            print(f'   签名: {license_data["signature"][:16]}...')
            print(f'   输出文件: {output_file}')
            print(f'\n请将此文件重命名为 license.key 后放入客户程序目录。')

    elif choice == '2':
        if os.path.exists(PUBLIC_KEY_FILE):
            with open(PUBLIC_KEY_FILE, 'r') as f:
                content = f.read()
            print(f'\n公钥内容：')
            print(content)
            print(f'请将此内容复制到客户端的 license_manager.py 的 PUBLIC_KEY_PEM 变量中')
        else:
            print(f'公钥文件不存在，请先生成密钥对')

    elif choice == '3':
        print('退出')

    else:
        print('无效选项')


def print_usage():
    print('用法:')
    print('  python license_generator.py --auto-deploy <项目目录>    一键部署（推荐）')
    print('  python license_generator.py --generate-keys             生成密钥对')
    print('  python license_generator.py                            进入交互菜单')
    print()
    print('一键部署示例:')
    print('  python license_generator.py --auto-deploy C:\\项目管理系统')


def main():
    if not CRYPTO_AVAILABLE:
        print('加密库未安装')
        print('请执行: pip install cryptography')
        return

    if len(sys.argv) > 1:
        if sys.argv[1] == '--generate-keys':
            generate_key_pair()
            return
        elif sys.argv[1] in ('--help', '-h', '/?'):
            print_usage()
            return
        elif sys.argv[1] == '--auto-deploy':
            if len(sys.argv) < 3:
                print('请指定项目目录')
                print('用法: python license_generator.py --auto-deploy <项目目录>')
                return
            auto_deploy(sys.argv[2])
            return

    print('='*60)
    print('  河北鑫奥项目管理系统 - License 生成工具')
    print('='*60)

    if not os.path.exists(PRIVATE_KEY_FILE):
        print(f'\n私钥文件不存在')
        print(f'请先生成密钥对: python license_generator.py --generate-keys')
        return

    manual_generate()
    print('\n' + '='*60)


if __name__ == '__main__':
    main()
