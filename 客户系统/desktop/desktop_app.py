import io
import json
import os
import re
import sys
import sqlite3
import ctypes
import atexit
import traceback
import datetime
from urllib.parse import parse_qs, urlencode

os.environ['DESKTOP_MODE'] = 'true'

MUTEX_NAME = 'Zjxmgl_SingleInstance'


def get_app_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_ROOT = get_app_root()
if getattr(sys, 'frozen', False):
    sys.path.insert(0, APP_ROOT)
else:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CONFIG_FILE = os.path.join(APP_ROOT, 'config.json')
DB_DIR = os.path.join(APP_ROOT, 'desktop_data')
LOG_FILE = os.path.join(APP_ROOT, 'runtime.log')


def log(msg):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] {msg}\n')
        print(msg, flush=True)
    except Exception:
        pass


def read_data_root():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return config.get('data_root', '')
        except Exception:
            return ''
    return ''


def ensure_single_instance():
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not mutex:
        return False
    if ctypes.GetLastError() == 183:
        kernel32.CloseHandle(mutex)
        return False
    return True


def register_app_scheme():
    from PySide6.QtWebEngineCore import QWebEngineUrlScheme
    scheme = QWebEngineUrlScheme(b'app')
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
    scheme.setFlags(
        QWebEngineUrlScheme.SecureScheme
        | QWebEngineUrlScheme.ContentSecurityPolicyIgnored
        | QWebEngineUrlScheme.FetchApiAllowed
        | QWebEngineUrlScheme.CorsEnabled
    )
    QWebEngineUrlScheme.registerScheme(scheme)


class _FlaskHandlerCore:
    def __init__(self, flask_app, session_cookie, data_root, db_dir):
        self.flask_app = flask_app
        self.session_cookie = session_cookie
        self._buffers = []
        self.data_root = data_root
        self.db_dir = db_dir

    def handle(self, job):
        log(f'[scheme] handle被调用 method={str(job.requestMethod())} url={job.requestUrl().toString()}')
        try:
            from PySide6.QtCore import QByteArray, QUrl, QBuffer, QIODeviceBase

            method_bytes = job.requestMethod()
            method = method_bytes.data().decode() if hasattr(method_bytes, 'data') else str(method_bytes)
            url = job.requestUrl()
            path = url.path() if url.path() else '/'
            query = url.query() if url.query() else ''

            environ = {
                'REQUEST_METHOD': method,
                'PATH_INFO': path,
                'QUERY_STRING': query,
                'SCRIPT_NAME': '',
                'SERVER_NAME': 'app',
                'SERVER_PORT': '80',
                'SERVER_PROTOCOL': 'HTTP/1.1',
                'wsgi.version': (1, 0),
                'wsgi.url_scheme': 'app',
                'wsgi.input': io.BytesIO(b''),
                'wsgi.errors': sys.stderr,
                'wsgi.multithread': False,
                'wsgi.multiprocess': False,
                'wsgi.run_once': False,
                'werkzeug.socket': None,
                'HTTP_COOKIE': f'session={self.session_cookie}',
            }

            raw_headers = job.requestHeaders()
            try:
                header_list = list(raw_headers)
            except Exception:
                header_list = []

            for entry in header_list:
                try:
                    if hasattr(entry, '__len__') and len(entry) == 2:
                        key_bytes, val_bytes = entry
                    else:
                        key_bytes = entry
                        val_bytes = raw_headers.value(entry)
                    key_str = key_bytes.data().decode() if hasattr(key_bytes, 'data') else str(key_bytes)
                    val_str = val_bytes.data().decode() if hasattr(val_bytes, 'data') else str(val_bytes)
                except Exception:
                    continue

                key_upper = key_str.upper()
                if key_upper in ('HOST', 'CONNECTION', 'ACCEPT-ENCODING'):
                    continue
                http_key = 'HTTP_' + key_upper.replace('-', '_')
                environ[http_key] = val_str

                if key_upper == 'CONTENT-TYPE':
                    environ['CONTENT_TYPE'] = val_str
                elif key_upper == 'CONTENT-LENGTH':
                    try:
                        environ['CONTENT_LENGTH'] = int(val_str)
                    except Exception:
                        pass

            body_data = b''
            query_dict = dict(parse_qs(query)) if query else {}
            if query_dict.get('_xf') == ['1']:
                query_dict.pop('_xf')
                flat = {k: (v[0] if isinstance(v, list) else v) for k, v in query_dict.items()}
                body_data = urlencode(flat).encode('utf-8')
                method = 'POST'
                environ['REQUEST_METHOD'] = 'POST'
                environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
                environ['CONTENT_LENGTH'] = str(len(body_data))
                environ['wsgi.input'] = io.BytesIO(body_data)
                environ['QUERY_STRING'] = ''
                log(f'[scheme] _xf表单提交 body_len={len(body_data)} fields={list(flat.keys())}')
            elif method in ('POST', 'PUT', 'PATCH'):
                try:
                    if hasattr(job, 'requestBody'):
                        body_io = job.requestBody()
                        if body_io is not None:
                            if not body_io.isOpen():
                                body_io.open(QIODeviceBase.OpenModeFlag.ReadOnly)
                            body_data = bytes(body_io.readAll())
                except Exception:
                    pass
                log(f'[scheme] POST body len={len(body_data)} raw={body_data[:200]}')
                environ['wsgi.input'] = io.BytesIO(body_data)
                if body_data:
                    environ['CONTENT_LENGTH'] = str(len(body_data))

            environ['wsgi.input'] = io.BytesIO(body_data)
            if 'CONTENT_LENGTH' not in environ:
                environ['CONTENT_LENGTH'] = str(len(body_data))

            if body_data and 'CONTENT_TYPE' not in environ:
                first_char = body_data[0:1]
                if first_char in (b'[', b'{'):
                    environ['CONTENT_TYPE'] = 'application/json'

            response_headers = {}
            response_status = [200]

            def start_response(status, headers, exc_info=None):
                response_status[0] = int(status.split(' ', 1)[0])
                for h_name, h_val in headers:
                    response_headers[h_name] = h_val

            result = self.flask_app(environ, start_response)
            response_body_chunks = []
            try:
                for chunk in result:
                    response_body_chunks.append(chunk)
            finally:
                if hasattr(result, 'close'):
                    result.close()
            response_body = b''.join(response_body_chunks)

            if response_status[0] in (301, 302, 303, 307, 308):
                location = response_headers.get('Location', '')
                if location:
                    if location.startswith('/'):
                        location = 'app://app' + location
                    log(f'[scheme] 重定向到 {location}')
                    job.redirect(QUrl(location))
                    return

            content_type = response_headers.get('Content-Type', 'text/html; charset=utf-8')
            disposition = response_headers.get('Content-Disposition', '')
            if disposition and 'attachment' in disposition:
                filename = 'export.xlsx'
                try:
                    for part in disposition.split(';'):
                        part = part.strip()
                        if part.lower().startswith('filename='):
                            filename = part.split('=', 1)[1].strip(' \t"\'')
                            break
                except Exception:
                    pass

                save_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
                project_label = ''
                if self.data_root:
                    m = re.search(r'/project/(\d+)', path)
                    if m:
                        pid = m.group(1)
                        try:
                            db_path = os.path.join(self.db_dir, 'desktop_system.db')
                            conn = sqlite3.connect(db_path)
                            row = conn.execute('SELECT name FROM projects WHERE id=?', (int(pid),)).fetchone()
                            conn.close()
                            if row and row[0]:
                                project_label = f'{pid}-{row[0]}'
                        except Exception:
                            project_label = pid
                if project_label:
                    save_dir = os.path.join(self.data_root, project_label, '导出文件')

                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response_body)
                log(f'[scheme] 附件已保存 {filepath} size={len(response_body)}')
                display_path = save_dir.replace('\\', '/')
                html = f'''<html><body style="text-align:center;padding-top:60px;font-family:sans-serif;">
                    <h3>&#9989; 文件已保存</h3>
                    <p>{filename}</p>
                    <p style="color:#666">路径：{display_path}</p>
                    <p><a href="javascript:history.back()">返回上一页</a></p>
                    </body></html>'''
                buf = QBuffer()
                buf.setData(QByteArray(html.encode('utf-8')))
                buf.open(QIODeviceBase.OpenModeFlag.ReadOnly)
                self._buffers.append(buf)
                job.reply(b'text/html; charset=utf-8', buf)
                return

            reply_body = QByteArray(response_body)
            buf = QBuffer()
            buf.setData(reply_body)
            buf.open(QIODeviceBase.OpenModeFlag.ReadOnly)
            self._buffers.append(buf)
            job.reply(content_type.encode('utf-8'), buf)
            log(f'[scheme] 响应 status={response_status[0]} size={len(response_body)}')

        except Exception:
            log(f'[scheme] 异常: {traceback.format_exc()}')
            try:
                err_buf = QBuffer()
                err_buf.setData(b'<h1>500</h1>')
                err_buf.open(QIODeviceBase.OpenModeFlag.ReadOnly)
                self._buffers.append(err_buf)
                job.reply(b'text/html; charset=utf-8', err_buf)
            except Exception:
                pass


def main():
    log('===== 启动 =====')
    log(f'APP_ROOT={APP_ROOT}')
    log(f'frozen={getattr(sys, "frozen", False)}')
    log(f'sys.executable={sys.executable}')

    if not ensure_single_instance():
        log('退出: 程序已在运行中')
        sys.exit(0)

    os.makedirs(DB_DIR, exist_ok=True)
    os.environ['DESKTOP_DB_DIR'] = DB_DIR
    os.environ['DESKTOP_CONFIG_DIR'] = APP_ROOT

    log('步骤1: 创建QApplication...')
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        app.setApplicationName('咨询项目管理系统')
        log('步骤1: QApplication创建OK')
    except Exception as e:
        log(f'步骤1失败: {traceback.format_exc()}')
        sys.exit(1)

    try:
        from desktop.first_run_config import check_first_run, run_first_run_config
        log(f'first_run_config导入OK, CONFIG_FILE检查={os.path.exists(CONFIG_FILE)}')
    except Exception as e:
        log(f'first_run_config导入失败: {traceback.format_exc()}')
        sys.exit(1)

    if not check_first_run():
        log('首次运行，弹出配置对话框...')
        try:
            data_root = run_first_run_config()
        except Exception as e:
            log(f'run_first_run_config崩溃: {traceback.format_exc()}')
            QMessageBox.critical(None, '启动失败', f'配置对话框异常:\n{e}')
            sys.exit(1)
        log(f'run_first_run_config返回: {repr(data_root)}')
        if data_root:
            os.environ['UPLOAD_FOLDER'] = data_root
            os.environ['DATA_ROOT'] = data_root
            log(f'用户选择了存储路径: {data_root}')
        else:
            log('用户取消了配置，退出')
            sys.exit(0)
    else:
        log(f'已有配置: {read_data_root()}')

    log(f'DB_DIR={DB_DIR}')
    log(f'DATA_ROOT={read_data_root()}')

    log('步骤2: 导入Flask...')
    try:
        from web.app import create_app
        log('步骤2: Flask导入OK')
    except Exception:
        log(f'步骤2失败: {traceback.format_exc()}')
        QMessageBox.critical(None, '启动失败', '导入Flask模块失败')
        sys.exit(1)

    log('步骤3: 创建Flask应用...')
    try:
        flask_app = create_app()
        data_root = read_data_root()
        if data_root:
            flask_app.config['STANDARD_FILES_FOLDER'] = os.path.join(data_root, '常用文件')

        with flask_app.test_request_context():
            from web.models import User
            from flask_login import login_user
            from flask import session as flask_session
            admin = User.query.filter_by(username='admin').first()
            if admin:
                login_user(admin, remember=True)
                serializer = flask_app.session_interface.get_signing_serializer(flask_app)
                admin_session = serializer.dumps(dict(flask_session))
                log(f'[login] 预登录成功, session_len={len(admin_session)}')
            else:
                admin_session = ''
                log('[login] 未找到admin用户')

        log('步骤3: 创建OK')
    except Exception:
        log(f'步骤3失败: {traceback.format_exc()}')
        QMessageBox.critical(None, '启动失败', '创建Flask应用失败')
        sys.exit(1)

    log('步骤4: 注册app:// scheme + 安装handler...')
    try:
        register_app_scheme()
        from PySide6.QtWebEngineCore import QWebEngineUrlSchemeHandler, QWebEngineProfile

        class PySchemeHandler(QWebEngineUrlSchemeHandler):
            def __init__(self, core):
                super().__init__()
                self._core = core
            def requestStarted(self, job):
                self._core.handle(job)

        core = _FlaskHandlerCore(flask_app, admin_session, read_data_root(), DB_DIR)
        handler = PySchemeHandler(core)
        QWebEngineProfile.defaultProfile().installUrlSchemeHandler(b'app', handler)

        from PySide6.QtWebEngineCore import QWebEngineScript
        script = QWebEngineScript()
        script.setName('form-interceptor')
        script.setSourceCode(r"""
(function() {
    document.addEventListener('submit', function(e) {
        var form = e.target;
        var method = (form.getAttribute('method') || 'get').toLowerCase();
        if (method !== 'post') return;
        var action = form.getAttribute('action') || '';
        if (!(action.startsWith('/') || action.startsWith('app://'))) return;
        e.preventDefault();
        e.stopPropagation();
        var fd = new FormData(form);
        var params = new URLSearchParams(fd).toString();
        if (action.startsWith('/')) action = 'app://app' + action;
        var sep = action.indexOf('?') >= 0 ? '&' : '?';
        window.location.href = action + sep + '_xf=1&' + params;
    }, true);
})();
""")
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(True)
        QWebEngineProfile.defaultProfile().scripts().insert(script)
        log('步骤4: scheme注册OK + 表单拦截JS已注入')
    except Exception:
        log(f'步骤4失败: {traceback.format_exc()}')
        QMessageBox.critical(None, '启动失败', f'scheme注册失败:\n{traceback.format_exc()}')
        sys.exit(1)

    log('步骤5: 创建主窗口...')
    try:
        from desktop.main_window import EstimateStudioWindow
        window = EstimateStudioWindow()
        window.show()
        log('步骤5: 主窗口已显示')
    except Exception:
        log(f'步骤5失败: {traceback.format_exc()}')
        QMessageBox.critical(None, '启动失败', '创建窗口失败')
        sys.exit(1)

    atexit.register(lambda: log('===== 退出 ====='))

    log('步骤6: 进入事件循环')
    exit_code = app.exec()
    log(f'事件循环结束, exit_code={exit_code}')
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
