import json
import os
import sys
import threading
import time
import urllib.request

os.environ['DESKTOP_MODE'] = 'true'

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')


def read_data_root():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return config.get('data_root', '')
        except Exception:
            return ''
    return ''


def wait_for_flask(url, timeout=15, interval=0.3):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(interval)
    return False


def start_flask():
    data_root = read_data_root()
    if data_root:
        os.environ['UPLOAD_FOLDER'] = data_root
        os.environ['DATA_ROOT'] = data_root

    from web.app import create_app
    app = create_app()

    if data_root:
        app.config['STANDARD_FILES_FOLDER'] = os.path.join(data_root, '常用文件')

    app.run(host='127.0.0.1', port=5005, debug=False, use_reloader=False)


def main():
    from PySide6.QtWidgets import QApplication
    from desktop.first_run_config import check_first_run, run_first_run_config

    app = QApplication(sys.argv)
    app.setApplicationName('Estimate Studio')

    if not check_first_run():
        data_root = run_first_run_config()
        if data_root:
            os.environ['UPLOAD_FOLDER'] = data_root
            os.environ['DATA_ROOT'] = data_root

    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    if not wait_for_flask('http://127.0.0.1:5005'):
        print('启动失败：Flask 服务未能在规定时间内启动')
        sys.exit(1)

    from desktop.main_window import EstimateStudioWindow
    window = EstimateStudioWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()