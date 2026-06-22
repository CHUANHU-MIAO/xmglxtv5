from web.app import create_app
import os

from license_manager import check_license_or_exit
check_license_or_exit()

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    use_waitress = os.environ.get('USE_FLASK_DEV', '').lower() not in ('1', 'true', 'yes')
    if use_waitress:
        from waitress import serve
        print(f'[waitress] 多线程模式启动 http://0.0.0.0:{port} (threads=8)')
        serve(app, host='0.0.0.0', port=port, threads=8)
    else:
        print(f'[Flask] 开发模式启动 http://0.0.0.0:{port}')
        app.run(host='0.0.0.0', port=port, debug=True)