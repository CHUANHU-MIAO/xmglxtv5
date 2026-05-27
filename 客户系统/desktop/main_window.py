import json
import os
import sys
import re
import sqlite3

from PySide6.QtCore import QUrl, Qt, QTimer, QSize, QPoint, QRect
from PySide6.QtGui import QAction, QIcon, QFont, QPixmap, QImage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QVBoxLayout, QWidget, QSizePolicy, QFrame, QScrollArea,
    QInputDialog, QMenu, QSplitter,
)

from desktop.subscription import SubscriptionClient


def _get_app_root():
    config_dir = os.environ.get('DESKTOP_CONFIG_DIR', '')
    if config_dir:
        return config_dir
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_ROOT = _get_app_root()
CONFIG_FILE = os.path.join(APP_ROOT, 'config.json')
FLASK_BASE = 'app://app'
DB_PATH = os.path.join(APP_ROOT, 'desktop_data', 'desktop_system.db')

ADD_PROJECT_FORM_JS = """
(function() {
    var form = document.querySelector('form');
    if (form && form.action && form.action.indexOf('/project/add') !== -1) {
        return JSON.stringify({found: true, action: form.action});
    }
    return JSON.stringify({found: false});
})();
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
        self.setWindowTitle('咨询项目管理系统')
        self.setFixedSize(400, 440)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._setup_ui()
        self._load_saved_credentials()

    def _setup_ui(self):
        self.setStyleSheet('''
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8fafc, stop:1 #f1f5f9);
                border: 1px solid rgba(0,0,0,0.06);
            }
        ''')

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        header.setFixedHeight(120)
        header.setStyleSheet('''
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #0f3460);
            }
        ''')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(32, 24, 32, 20)
        header_layout.setSpacing(4)

        icon_label = QLabel('📋')
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet('font-size: 32px; background: transparent;')
        header_layout.addWidget(icon_label)

        title = QLabel('咨询项目管理系统')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 20px; font-weight: 700; color: #ffffff; background: transparent; letter-spacing: 0.3px;')
        header_layout.addWidget(title)

        subtitle = QLabel('登录以验证订阅授权')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('font-size: 12px; color: rgba(255,255,255,0.55); background: transparent;')
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(32, 24, 32, 24)
        body_layout.setSpacing(0)

        input_style = '''
            QLineEdit {
                padding: 10px 14px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 14px;
                color: #1e293b;
                background: #ffffff;
            }
            QLineEdit:focus {
                border-color: #10b981;
                background: #ffffff;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
            }
        '''

        label_style = 'font-size: 12px; font-weight: 600; color: #475569; padding-bottom: 4px;'

        username_label = QLabel('用户名')
        username_label.setStyleSheet(label_style)
        body_layout.addWidget(username_label)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText('请输入您的用户名')
        self.username_edit.setStyleSheet(input_style)
        body_layout.addWidget(self.username_edit)

        body_layout.addSpacing(14)

        password_label = QLabel('密码')
        password_label.setStyleSheet(label_style)
        body_layout.addWidget(password_label)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText('请输入密码')
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet(input_style)
        body_layout.addWidget(self.password_edit)

        body_layout.addSpacing(10)

        remember_layout = QHBoxLayout()
        remember_layout.setContentsMargins(0, 0, 0, 0)
        remember_layout.setSpacing(16)

        self.remember_user_cb = QCheckBox('记住用户名')
        self.remember_user_cb.setStyleSheet('font-size: 12px; color: #64748b;')
        remember_layout.addWidget(self.remember_user_cb)

        self.remember_pwd_cb = QCheckBox('记住密码')
        self.remember_pwd_cb.setStyleSheet('font-size: 12px; color: #64748b;')
        remember_layout.addWidget(self.remember_pwd_cb)

        remember_layout.addSpacing(12)

        self.forgot_pwd_label = QLabel('找回密码')
        self.forgot_pwd_label.setCursor(Qt.PointingHandCursor)
        self.forgot_pwd_label.setStyleSheet('font-size: 12px; color: #0d6efd;')
        self.forgot_pwd_label.mousePressEvent = self._on_forgot_password
        remember_layout.addWidget(self.forgot_pwd_label)

        remember_layout.addStretch()
        body_layout.addLayout(remember_layout)

        body_layout.addSpacing(6)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedHeight(32)
        self.status_label.setStyleSheet('font-size: 12px; color: #ef4444; padding: 4px 0;')
        body_layout.addWidget(self.status_label)

        body_layout.addSpacing(4)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self.login_btn = QPushButton('登 录')
        self.login_btn.setDefault(True)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet('''
            QPushButton {
                padding: 10px 24px; background: #10b981; color: white;
                border: none; border-radius: 8px; font-size: 14px; font-weight: 700;
            }
            QPushButton:hover { background: #059669; }
            QPushButton:disabled { background: #94a3b8; }
        ''')
        btn_layout.addWidget(self.login_btn)

        self.register_btn = QPushButton('注 册')
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.setStyleSheet('''
            QPushButton {
                padding: 10px 24px; background: transparent; color: #64748b;
                border: 2px solid #e2e8f0; border-radius: 8px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { border-color: #10b981; color: #10b981; }
        ''')
        btn_layout.addWidget(self.register_btn)
        body_layout.addLayout(btn_layout)

        layout.addWidget(body, stretch=1)

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

    def _on_forgot_password(self, event):
        import webbrowser
        webbrowser.open(f'{self.client.server_url}/forgot-password')


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


class ZjxmglWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('咨询项目管理系统')
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self._logged_in = False
        self._web_authenticated = False
        self._pending_nav = None
        self._current_project_id = None
        self._subscription_level = 'standard'
        self._max_projects = 5
        self._subscription_client = None
        self.projects = []
        self._view_mode = 'tree'
        self._sort_mode = 'time'
        self._setup_ui()
        self._show_login_dialog()

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
        brand = QLabel('咨询项目管理系统')
        brand.setStyleSheet('font-size: 17px; font-weight: 700; color: #0d6efd; padding: 8px 8px 4px 8px;')
        sidebar_layout.addWidget(brand)

        # User info
        self.user_label = QLabel('未登录')
        self.user_label.setStyleSheet('font-size: 11px; color: #6c757d; padding: 0px 8px 2px 8px;')
        sidebar_layout.addWidget(self.user_label)

        # Subscription info (clickable)
        self.sub_label = QLabel('')
        self.sub_label.setCursor(Qt.PointingHandCursor)
        self.sub_label.setStyleSheet('font-size: 11px; color: #10b981; padding: 0px 8px 10px 8px; text-decoration: underline;')
        self.sub_label.mousePressEvent = lambda e: self._open_pricing()
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
        self.btn_sort_toggle.setVisible(False)
        view_layout.addWidget(self.btn_sort_toggle)

        sidebar_layout.addWidget(view_ctrl)

        self.projects_label = QLabel('项 目')
        self.projects_label.setStyleSheet('font-size: 11px; color: #adb5bd; padding: 2px 8px 2px 8px; font-weight: 600;')
        sidebar_layout.addWidget(self.projects_label)

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
        main_layout.addWidget(self.web_view)

    def _show_login_dialog(self):
        self._subscription_client = SubscriptionClient()
        dlg = SubscriptionDialog(self._subscription_client, self)
        if dlg.exec() == QDialog.Accepted:
            self._logged_in = True
            self._update_subscription_info()
            self._init_web_view()
        else:
            QTimer.singleShot(100, self.close)

    def _open_pricing(self):
        import webbrowser
        webbrowser.open(f'{self._subscription_client.server_url}/pricing')

    def _update_subscription_info(self):
        if not self._subscription_client or not self._subscription_client.user_info:
            return
        username = self._subscription_client.user_info.get('username', '用户')
        sub = self._subscription_client.user_info.get('subscription', {})
        level = sub.get('level', 'standard')
        self._subscription_level = level
        limits = SUBSCRIPTION_LIMITS.get(level, SUBSCRIPTION_LIMITS['standard'])
        self._max_projects = limits['max_projects']
        expire = sub.get('expire_date', '未知')
        label = limits['label']
        self.user_label.setText(f'用户：{username}')
        self.user_label.setStyleSheet('font-size: 11px; color: #1e293b; font-weight: 600; padding: 0px 8px 2px 8px;')
        expire_text = expire if expire != '未知' else '永久'
        self.sub_label.setText(f'{label} | 到期 {expire_text}')

    def _init_web_view(self):
        self._pending_nav = 'search'
        self._extract_projects()
        self.web_view.load(QUrl(f'{FLASK_BASE}/my_projects'))

    def _navigate_to(self, target):
        for btn in [self.btn_add, self.btn_search, self.btn_files]:
            btn.set_active(btn.page_id == target)

        if not self._logged_in:
            return

        self._pending_nav = target
        url = self._target_url(target)
        if url:
            self.web_view.load(QUrl(url))

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

    def _on_page_loaded(self, ok):
        if not ok:
            QTimer.singleShot(300, lambda: self.web_view.reload())
            return
        url = self.web_view.url().toString()
        self._web_authenticated = True
        self._update_subscription_info()
        self._on_check_current_url(url)

    def _on_check_current_url(self, url):
        if '/my_projects' in url:
            QTimer.singleShot(200, self._extract_projects)
        elif '/project/add' in url:
            QTimer.singleShot(200, self._on_add_project_page_loaded)
        else:
            QTimer.singleShot(200, self._extract_projects)

    def _extract_projects(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute(
                'SELECT id, name, start_date FROM projects WHERE is_valid = 1 ORDER BY start_date DESC'
            )
            rows = cursor.fetchall()
            conn.close()
            data = [{'id': r[0], 'name': r[1], 'start_date': r[2] or ''} for r in rows]
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
            self.btn_sort_toggle.setVisible(True)
        else:
            self._view_mode = 'tree'
            self.btn_view_toggle.setText('📅 时间序列')
            self.btn_sort_toggle.setVisible(False)

        if self.projects:
            self._update_project_list(self.projects)

    def _toggle_sort_mode(self):
        if self._sort_mode == 'time':
            self._sort_mode = 'name'
            self.btn_sort_toggle.setText('🔤 按名称')
        else:
            self._sort_mode = 'time'
            self.btn_sort_toggle.setText('⏱ 按时间')

        if self._view_mode == 'list' and self.projects:
            self._update_project_list(self.projects)

    def _on_project_click(self, project_id):
        self._navigate_to(project_id)

    def _on_add_project_page_loaded(self):
        self.web_view.page().runJavaScript(ADD_PROJECT_FORM_JS, self._on_check_add_form)

    def _on_check_add_form(self, result_str):
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
    app.setApplicationName('咨询项目管理系统')
    window = ZjxmglWindow()
    window.show()
    sys.exit(app.exec())