import json
import os
import sys
import re

from PySide6.QtCore import QUrl, Qt, QTimer, QSize, QPoint, QRect
from PySide6.QtGui import QAction, QIcon, QFont, QPixmap, QImage
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QVBoxLayout, QWidget, QSizePolicy, QFrame, QScrollArea,
    QInputDialog, QMenu, QSplitter, QListWidget, QListWidgetItem,
    QToolTip,
)

from desktop.subscription import SubscriptionClient

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
FLASK_BASE = 'http://127.0.0.1:5005'

LOGIN_JS = """
(function() {
    var u = document.querySelector('input[name="username"]');
    var p = document.querySelector('input[name="password"]');
    var f = document.querySelector('form');
    if (u && p && f) {
        var formData = new FormData(f);
        formData.set('username', 'admin');
        formData.set('password', 'admin123');
        return fetch(f.action || '/auth/login', {
            method: 'POST',
            body: new URLSearchParams(formData)
        }).then(function(resp) {
            if (resp.redirected) {
                return JSON.stringify({ok: true});
            }
            return JSON.stringify({ok: false, url: window.location.href});
        }).catch(function() {
            return JSON.stringify({ok: false, url: window.location.href});
        });
    }
    return Promise.resolve(JSON.stringify({ok: false, url: window.location.href}));
})();
"""

GET_PROJECTS_JS = """
(function() {
    return fetch('/api/projects/search?per_page=200')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                return JSON.stringify(d.rows.map(function(p) {
                    return {id: p.id, name: p.name, start_date: p.start_date || ''};
                }));
            }
            return '[]';
        })
        .catch(function() { return '[]'; });
})();
"""

ADD_PROJECT_FORM_JS = """
(function() {
    var form = document.querySelector('form');
    if (form && form.action && form.action.indexOf('/project/add') !== -1) {
        return JSON.stringify({found: true, action: form.action});
    }
    return JSON.stringify({found: false});
})();
"""

INJECT_DETAIL_BUTTONS_JS = """
(function(projectId) {
    var container = document.querySelector('.container.mt-5.py-4') || document.querySelector('.container');
    if (!container) return JSON.stringify({ok: false, msg: 'container not found'});
    if (document.getElementById('desktop-detail-buttons')) return JSON.stringify({ok: false, msg: 'already injected'});
    var bar = document.createElement('div');
    bar.id = 'desktop-detail-buttons';
    bar.style.cssText = 'background: #f0f4ff; border: 1px solid #d0d9f0; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; text-align: center;';
    bar.innerHTML = '<div style="font-size:13px;color:#6c757d;margin-bottom:10px;">测算功能</div>' +
        '<div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">' +
        '<a href="/project/' + projectId + '/investment" class="btn btn-primary" style="padding:8px 28px;font-size:15px;font-weight:600;border-radius:8px;text-decoration:none;">投资估算</a>' +
        '<a href="/project/' + projectId + '/energy" class="btn btn-success" style="padding:8px 28px;font-size:15px;font-weight:600;border-radius:8px;text-decoration:none;">能耗估算</a>' +
        '<a href="/project/' + projectId + '/finance" class="btn btn-info" style="padding:8px 28px;font-size:15px;font-weight:600;border-radius:8px;text-decoration:none;color:#fff;">财务测算</a>' +
        '</div>';
    container.insertBefore(bar, container.firstChild);
    return JSON.stringify({ok: true});
})();
"""

GET_PAGE_URL_JS = """
(function() { return window.location.href; })();
"""

SUBSCRIPTION_LIMITS = {
    'standard': {'label': '标准版', 'max_projects': 5},
    'pro': {'label': '专业版', 'max_projects': 50},
    'max': {'label': '旗舰版', 'max_projects': 999999},
}


class SubscriptionDialog(QDialog):
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle('Estimate Studio - 登录')
        self.setFixedSize(400, 340)
        self._setup_ui()
        self._load_saved_credentials()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel('Estimate Studio')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 22px; font-weight: 700; color: #0d6efd; margin-bottom: 4px;')
        layout.addWidget(title)

        subtitle = QLabel('请登录以验证订阅')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('font-size: 13px; color: #6c757d; margin-bottom: 4px;')
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText('请输入用户名')
        self.username_edit.setStyleSheet('padding: 8px 12px; border: 1px solid #ced4da; border-radius: 6px; font-size: 14px;')
        form.addRow('用户名：', self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText('请输入密码')
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet('padding: 8px 12px; border: 1px solid #ced4da; border-radius: 6px; font-size: 14px;')
        form.addRow('密　码：', self.password_edit)
        layout.addLayout(form)

        # Remember options
        remember_layout = QHBoxLayout()
        remember_layout.setSpacing(16)
        remember_layout.setContentsMargins(4, 0, 4, 0)

        self.remember_user_cb = QCheckBox('记住用户名')
        self.remember_user_cb.setStyleSheet('font-size: 12px; color: #495057;')
        remember_layout.addWidget(self.remember_user_cb)

        self.remember_pwd_cb = QCheckBox('记住密码')
        self.remember_pwd_cb.setStyleSheet('font-size: 12px; color: #495057;')
        remember_layout.addWidget(self.remember_pwd_cb)

        remember_layout.addStretch()
        layout.addLayout(remember_layout)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet('font-size: 12px; color: #dc3545; min-height: 20px;')
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.login_btn = QPushButton('登 录')
        self.login_btn.setDefault(True)
        self.login_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 24px; background: #0d6efd; color: white;
                border: none; border-radius: 6px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: #0b5ed7; }
            QPushButton:disabled { background: #6c757d; }
        ''')
        btn_layout.addWidget(self.login_btn)

        self.register_btn = QPushButton('注 册')
        self.register_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 24px; background: #198754; color: white;
                border: none; border-radius: 6px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: #157347; }
        ''')
        btn_layout.addWidget(self.register_btn)
        layout.addLayout(btn_layout)

        self.server_label = QLabel(f'服务器: {self.client.server_url}')
        self.server_label.setAlignment(Qt.AlignCenter)
        self.server_label.setStyleSheet('font-size: 11px; color: #adb5bd;')
        layout.addWidget(self.server_label)

        self.login_btn.clicked.connect(self._on_login)
        self.register_btn.clicked.connect(self._on_register)
        self.password_edit.returnPressed.connect(self._on_login)

    def _load_saved_credentials(self):
        username, password, remember = self.client.get_saved_credentials()
        if username:
            self.username_edit.setText(username)
            self.remember_user_cb.setChecked(True)
        if remember and password:
            self.password_edit.setText(password)
            self.remember_pwd_cb.setChecked(True)

    def _on_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            self.status_label.setText('请输入用户名和密码')
            return
        self.login_btn.setEnabled(False)
        self.status_label.setStyleSheet('font-size: 12px; color: #0d6efd; min-height: 20px;')
        self.status_label.setText('正在登录...')
        QApplication.processEvents()
        ok, msg = self.client.login(username, password)
        if ok:
            if self.remember_user_cb.isChecked():
                self.client.save_credentials(
                    username, password,
                    remember_password=self.remember_pwd_cb.isChecked()
                )
            else:
                self.client.save_credentials('', '', False)
            self.accept()
        else:
            self.status_label.setStyleSheet('font-size: 12px; color: #dc3545; min-height: 20px;')
            self.status_label.setText(msg)
            self.login_btn.setEnabled(True)

    def _on_register(self):
        import webbrowser
        webbrowser.open(f'{self.client.server_url}/register')


class NavButton(QPushButton):
    def __init__(self, text, page_id, icon_char=''):
        super().__init__()
        self.page_id = page_id
        display = f'{icon_char}  {text}' if icon_char else text
        self.setText(display)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(self._normal_style())

    def _normal_style(self):
        return '''
            QPushButton {
                text-align: left; padding: 8px 16px;
                border: none; border-radius: 6px;
                font-size: 13px; color: #495057;
                background: transparent;
            }
            QPushButton:hover {
                background: #e9ecef;
            }
            QPushButton:checked {
                background: #0d6efd; color: white; font-weight: 600;
            }
        '''

    def set_active(self, active):
        self.setChecked(active)


class ProjectNavButton(QPushButton):
    def __init__(self, project_id, project_name):
        super().__init__()
        self.project_id = project_id
        self.setText(f'  {project_name}')
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet('''
            QPushButton {
                text-align: left; padding: 5px 16px 5px 28px;
                border: none; border-radius: 4px;
                font-size: 12px; color: #495057;
                background: transparent;
            }
            QPushButton:hover {
                background: #e9ecef;
            }
            QPushButton:checked {
                background: #cfe2ff; color: #0d6efd; font-weight: 600;
            }
        ''')

    def set_active(self, active):
        self.setChecked(active)


class MonthGroupWidget(QWidget):
    def __init__(self, month, projects, on_project_click, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._month = month
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        month_label = f'{month}月' if month else '未分类'
        self.header = QPushButton(f'  ▶  {month_label}  ({len(projects)})')
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setMinimumHeight(30)
        self.header.setStyleSheet('''
            QPushButton {
                text-align: left; padding: 3px 12px 3px 20px;
                border: none; border-radius: 4px;
                font-size: 12px; color: #6c757d;
                background: transparent;
            }
            QPushButton:hover {
                background: #e9ecef;
                color: #495057;
            }
        ''')
        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(16, 0, 0, 0)
        self.content_layout.setSpacing(1)
        self.content.setVisible(False)
        layout.addWidget(self.content)

        for p in projects:
            btn = ProjectNavButton(p['id'], p['name'][:22])
            btn.clicked.connect(lambda checked, pid=p['id']: on_project_click(pid))
            self.content_layout.addWidget(btn)

    def _toggle(self):
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        arrow = '▼' if self._expanded else '▶'
        month_label = f'{self._month}月' if self._month else '未分类'
        count = self.content_layout.count()
        self.header.setText(f'  {arrow}  {month_label}  ({count})')


class YearGroupWidget(QWidget):
    def __init__(self, year, months_dict, on_project_click, parent=None):
        super().__init__(parent)
        self._expanded = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        total = sum(len(projs) for projs in months_dict.values())
        self.header = QPushButton(f'  ▶  {year}年  ({total})')
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setMinimumHeight(34)
        self.header.setStyleSheet('''
            QPushButton {
                text-align: left; padding: 5px 12px 5px 8px;
                border: none; border-radius: 4px;
                font-size: 13px; font-weight: 600; color: #343a40;
                background: #f0f0f0;
            }
            QPushButton:hover {
                background: #e2e6ea;
            }
        ''')
        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(12, 0, 0, 0)
        self.content_layout.setSpacing(1)
        self.content.setVisible(False)
        layout.addWidget(self.content)

        sorted_months = sorted(months_dict.keys(), reverse=True)
        for month in sorted_months:
            projs = months_dict[month]
            mw = MonthGroupWidget(month, projs, on_project_click)
            self.content_layout.addWidget(mw)

    def _toggle(self):
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        arrow = '▼' if self._expanded else '▶'
        self.header.setText(self.header.text().replace('▶' if not self._expanded else '▼', arrow))


class EstimateStudioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Estimate Studio')
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self._logged_in = False
        self._web_authenticated = False
        self.projects = []
        self._pending_nav = None
        self._current_project_id = None
        self._subscription_level = 'standard'
        self._max_projects = 5
        self._subscription_client = None
        self._view_mode = 'tree'
        self._sort_mode = 'time'
        self._setup_ui()
        self._check_subscription()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ====== Left sidebar ======
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet('background: #f8f9fa; border-right: 1px solid #dee2e6;')
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 12, 10, 12)
        sidebar_layout.setSpacing(2)

        # Brand
        brand = QLabel('Estimate Studio')
        brand.setStyleSheet('font-size: 17px; font-weight: 700; color: #0d6efd; padding: 8px 8px 12px 8px;')
        sidebar_layout.addWidget(brand)

        # Subscription info
        self.sub_label = QLabel('订阅: -')
        self.sub_label.setStyleSheet('font-size: 11px; color: #6c757d; padding: 2px 8px 10px 8px;')
        sidebar_layout.addWidget(self.sub_label)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet('color: #dee2e6;')
        sidebar_layout.addWidget(sep1)

        # ====== Navigation Buttons ======
        self.btn_add = NavButton('添加项目', 'add', '\u2795')
        self.btn_add.clicked.connect(lambda: self._navigate_to('add'))
        sidebar_layout.addWidget(self.btn_add)

        self.btn_search = NavButton('搜索项目', 'search', '\uD83D\uDD0D')
        self.btn_search.clicked.connect(lambda: self._navigate_to('search'))
        sidebar_layout.addWidget(self.btn_search)

        self.btn_files = NavButton('常用文件', 'files', '\uD83D\uDCC1')
        self.btn_files.clicked.connect(lambda: self._navigate_to('files'))
        sidebar_layout.addWidget(self.btn_files)

        # Separator before project list
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet('color: #dee2e6;')
        sidebar_layout.addWidget(sep2)

        # ====== View Controls ======
        view_ctrl = QWidget()
        view_ctrl.setStyleSheet('padding: 0px;')
        view_layout = QHBoxLayout(view_ctrl)
        view_layout.setContentsMargins(4, 4, 4, 2)
        view_layout.setSpacing(4)

        self.btn_view_toggle = QPushButton('📅 时间序列')
        self.btn_view_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_view_toggle.setMinimumHeight(28)
        self.btn_view_toggle.setStyleSheet('''
            QPushButton {
                padding: 3px 8px; border: 1px solid #ced4da;
                border-radius: 4px; font-size: 11px; color: #495057;
                background: #ffffff;
            }
            QPushButton:hover {
                background: #e9ecef; border-color: #adb5bd;
            }
        ''')
        self.btn_view_toggle.clicked.connect(self._toggle_view_mode)
        view_layout.addWidget(self.btn_view_toggle)

        self.btn_sort_toggle = QPushButton('⏱ 按时间')
        self.btn_sort_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_sort_toggle.setMinimumHeight(28)
        self.btn_sort_toggle.setStyleSheet('''
            QPushButton {
                padding: 3px 8px; border: 1px solid #ced4da;
                border-radius: 4px; font-size: 11px; color: #495057;
                background: #ffffff;
            }
            QPushButton:hover {
                background: #e9ecef; border-color: #adb5bd;
            }
        ''')
        self.btn_sort_toggle.clicked.connect(self._toggle_sort_mode)
        view_layout.addWidget(self.btn_sort_toggle)

        sidebar_layout.addWidget(view_ctrl)

        # Project list label
        self.projects_label = QLabel('项 目')
        self.projects_label.setStyleSheet('font-size: 11px; color: #adb5bd; padding: 2px 8px 2px 8px; font-weight: 600;')
        sidebar_layout.addWidget(self.projects_label)

        # Scrollable project list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet('QScrollArea { border: none; background: transparent; }')
        self.project_list_widget = QWidget()
        self.project_list_layout = QVBoxLayout(self.project_list_widget)
        self.project_list_layout.setContentsMargins(0, 0, 0, 0)
        self.project_list_layout.setSpacing(1)
        self.project_list_layout.addStretch()
        scroll.setWidget(self.project_list_widget)
        sidebar_layout.addWidget(scroll, stretch=1)

        # Version
        version_label = QLabel('v5.0.1')
        version_label.setStyleSheet('font-size: 11px; color: #adb5bd; padding: 8px;')
        version_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(sidebar)

        # ====== Web View ======
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet('border: none;')
        self.web_view.loadFinished.connect(self._on_page_loaded)
        self._setup_global_scripts()
        main_layout.addWidget(self.web_view)

    def _setup_global_scripts(self):
        script = QWebEngineScript()
        script.setName('desktop_hide_nav')
        script.setSourceCode('''
(function() {
    var s = document.getElementById('desktop-hide-nav');
    if (!s) {
        s = document.createElement('style');
        s.id = 'desktop-hide-nav';
        s.textContent = 'nav.navbar{display:none!important}.page-content{padding-top:0!important}body{padding-top:0!important}';
        (document.head || document.documentElement).appendChild(s);
    }
})();
''')
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setWorldId(QWebEngineScript.MainWorld)
        self.web_view.page().scripts().insert(script)

    def _check_subscription(self):
        self._subscription_client = SubscriptionClient()
        valid, msg = self._subscription_client.verify()
        if valid:
            self._logged_in = True
            self._update_subscription_info()
            self._init_web_view()
            return

        dlg = SubscriptionDialog(self._subscription_client, self)
        if dlg.exec() == QDialog.Accepted:
            self._logged_in = True
            self._update_subscription_info()
            self._init_web_view()
        else:
            QTimer.singleShot(100, self.close)

    def _update_subscription_info(self):
        if not self._subscription_client or not self._subscription_client.user_info:
            return
        sub = self._subscription_client.user_info.get('subscription', {})
        level = sub.get('level', 'standard')
        self._subscription_level = level
        limits = SUBSCRIPTION_LIMITS.get(level, SUBSCRIPTION_LIMITS['standard'])
        self._max_projects = limits['max_projects']
        expire = sub.get('expire_date', '未知')
        label = limits['label']
        self.sub_label.setText(f'订阅: {label}  |  上限: {self._max_projects} 个')
        self.sub_label.setStyleSheet('font-size: 11px; color: #6c757d; padding: 2px 8px 10px 8px;')

    def _get_project_count(self):
        return len(self.projects)

    def _check_project_limit(self):
        count = self._get_project_count()
        if count >= self._max_projects:
            limits = SUBSCRIPTION_LIMITS.get(self._subscription_level, SUBSCRIPTION_LIMITS['standard'])
            QMessageBox.warning(self, '项目数量已达上限',
                f'您的当前订阅（{limits["label"]}）最多允许 {self._max_projects} 个项目。\n'
                f'当前已有 {count} 个项目。\n\n'
                '请升级订阅以创建更多项目。')
            return False
        return True

    def _init_web_view(self):
        self._pending_nav = 'list'
        self.web_view.load(QUrl(f'{FLASK_BASE}/auth/login'))

    def _navigate_to(self, target):
        for btn in [self.btn_add, self.btn_search, self.btn_files]:
            btn.set_active(btn.page_id == target)

        if not self._logged_in:
            return

        self._pending_nav = target

        if target == 'add' and not self._check_project_limit():
            self._pending_nav = None
            return

        if self._web_authenticated:
            url = self._target_url(target)
            if url:
                self.web_view.load(QUrl(url))
            return

        self.web_view.load(QUrl(f'{FLASK_BASE}/auth/login'))

    def _target_url(self, target):
        if target == 'add':
            return f'{FLASK_BASE}/project/add'
        elif target == 'search':
            return f'{FLASK_BASE}/my_projects'
        elif target == 'list':
            return f'{FLASK_BASE}/my_projects'
        elif target == 'files':
            return f'{FLASK_BASE}/admin/database'
        elif isinstance(target, int):
            self._current_project_id = target
            return f'{FLASK_BASE}/project/detail/{target}'
        return None

    def _get_project_buttons(self):
        buttons = []
        for i in range(self.project_list_layout.count()):
            w = self.project_list_layout.itemAt(i).widget()
            if isinstance(w, ProjectNavButton):
                buttons.append(w)
        return buttons

    def _on_project_click(self, project_id):
        self._navigate_to(project_id)

    def _on_page_loaded(self, ok):
        if not ok:
            QTimer.singleShot(800, lambda: self.web_view.reload())
            return
        url = self.web_view.url().toString()

        if '/auth/login' in url and self._logged_in:
            self.web_view.page().runJavaScript(LOGIN_JS, self._on_login_result)
        else:
            self.web_view.page().runJavaScript(GET_PAGE_URL_JS, self._on_check_current_url)

    def _on_login_result(self, result_str):
        if not result_str:
            QTimer.singleShot(1000, lambda: self.web_view.reload())
            return
        try:
            result = json.loads(result_str)
        except Exception:
            result = {}
        if result.get('ok'):
            self._web_authenticated = True
            target = self._pending_nav
            url = self._target_url(target)
            if url:
                self.web_view.load(QUrl(url))
            else:
                self.web_view.load(QUrl(f'{FLASK_BASE}/my_projects'))
            QTimer.singleShot(1500, self._delayed_extract_projects)
        else:
            QTimer.singleShot(800, lambda: self.web_view.reload())

    def _delayed_extract_projects(self):
        current_url = self.web_view.url().toString()
        if '/my_projects' in current_url:
            self._extract_projects()
        elif '/project/detail/' in current_url:
            self._inject_detail_buttons()

    def _on_check_current_url(self, url):
        if not url:
            return
        if '/my_projects' in url:
            QTimer.singleShot(300, self._extract_projects)
        elif '/project/detail/' in url:
            QTimer.singleShot(300, self._inject_detail_buttons)
        elif '/project/add' in url:
            QTimer.singleShot(400, self._on_add_project_page_loaded)

    def _extract_projects(self):
        self.web_view.page().runJavaScript(GET_PROJECTS_JS, self._on_projects_data)

    def _on_projects_data(self, json_str):
        if not json_str:
            return
        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                data = []
            self._update_project_list(data)
        except Exception:
            pass

    def _update_project_list(self, project_list):
        self.projects = project_list
        self._clear_project_list()

        if not project_list:
            self.project_list_layout.addStretch()
            return

        if self._view_mode == 'tree':
            self._build_tree_view()
        else:
            self._build_list_view()

        self._update_subscription_info()

    def _clear_project_list(self):
        while self.project_list_layout.count() > 0:
            item = self.project_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build_tree_view(self):
        groups = {}
        for p in self.projects:
            date_str = p.get('start_date', '')
            if date_str and len(date_str) >= 7:
                year = date_str[:4]
                month = str(int(date_str[5:7]))
            else:
                year = '未分类'
                month = ''

            if year not in groups:
                groups[year] = {}
            if month not in groups[year]:
                groups[year][month] = []
            groups[year][month].append(p)

        sorted_years = sorted(groups.keys(), reverse=True)

        for year in sorted_years:
            if year == '未分类':
                continue
            year_widget = YearGroupWidget(year, groups[year], self._on_project_click)
            self.project_list_layout.addWidget(year_widget)

        if '未分类' in groups and groups['未分类']:
            year_widget = YearGroupWidget('未分类', groups['未分类'], self._on_project_click)
            self.project_list_layout.addWidget(year_widget)

        self.project_list_layout.addStretch()

    def _build_list_view(self):
        sorted_projects = self._get_sorted_projects()

        for p in sorted_projects:
            btn = ProjectNavButton(p['id'], p['name'][:22])
            btn.clicked.connect(lambda checked, pid=p['id']: self._on_project_click(pid))
            self.project_list_layout.addWidget(btn)

        self.project_list_layout.addStretch()

    def _get_sorted_projects(self):
        if self._sort_mode == 'time':
            return sorted(self.projects,
                key=lambda p: p.get('start_date', '') or '9999-99-99')
        else:
            return sorted(self.projects,
                key=lambda p: p.get('name', '').lower())

    def _toggle_view_mode(self):
        if self._view_mode == 'tree':
            self._view_mode = 'list'
            self.btn_view_toggle.setText('📋 项目清单')
            QToolTip.showText(
                self.btn_view_toggle.mapToGlobal(QPoint(0, self.btn_view_toggle.height())),
                '当前视图：项目清单（列表模式）',
                self.btn_view_toggle, QRect(), 2000
            )
            self.btn_sort_toggle.setVisible(True)
        else:
            self._view_mode = 'tree'
            self.btn_view_toggle.setText('📅 时间序列')
            QToolTip.showText(
                self.btn_view_toggle.mapToGlobal(QPoint(0, self.btn_view_toggle.height())),
                '当前视图：时间序列（按年/月分类）',
                self.btn_view_toggle, QRect(), 2000
            )
            self.btn_sort_toggle.setVisible(False)

        if self.projects:
            self._update_project_list(self.projects)

    def _toggle_sort_mode(self):
        if self._sort_mode == 'time':
            self._sort_mode = 'name'
            self.btn_sort_toggle.setText('🔤 按名称')
            QToolTip.showText(
                self.btn_sort_toggle.mapToGlobal(QPoint(0, self.btn_sort_toggle.height())),
                '当前排序：按项目名称首字母',
                self.btn_sort_toggle, QRect(), 2000
            )
        else:
            self._sort_mode = 'time'
            self.btn_sort_toggle.setText('⏱ 按时间')
            QToolTip.showText(
                self.btn_sort_toggle.mapToGlobal(QPoint(0, self.btn_sort_toggle.height())),
                '当前排序：按开始时间',
                self.btn_sort_toggle, QRect(), 2000
            )

        if self._view_mode == 'list' and self.projects:
            self._update_project_list(self.projects)

    def _on_add_project_page_loaded(self):
        self.web_view.page().runJavaScript(ADD_PROJECT_FORM_JS, self._on_check_add_form)

    def _on_check_add_form(self, result_str):
        if not result_str:
            return
        try:
            result = json.loads(result_str)
        except Exception:
            pass

    def _inject_detail_buttons(self):
        project_id = self._current_project_id
        js = INJECT_DETAIL_BUTTONS_JS.replace('projectId', str(project_id))
        self.web_view.page().runJavaScript(js, self._on_inject_result)

    def _on_inject_result(self, result_str):
        if not result_str:
            return
        try:
            result = json.loads(result_str)
        except Exception:
            pass

    def closeEvent(self, event):
        event.accept()


def run_desktop_app():
    app = QApplication(sys.argv)
    app.setApplicationName('Estimate Studio')
    window = EstimateStudioWindow()
    window.show()
    sys.exit(app.exec())