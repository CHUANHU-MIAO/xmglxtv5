import json
import os

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')


class FirstRunConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Estimate Studio - 初始配置')
        self.setFixedSize(560, 300)
        self._data_root = ''
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 28)

        title = QLabel('欢迎使用 Estimate Studio')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 20px; font-weight: 700; color: #0d6efd;')
        layout.addWidget(title)

        desc = QLabel('请选择文件存储路径，项目文件、上传文件、测算数据等将保存在该目录下。')
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 13px; color: #6c757d; margin-bottom: 8px;')
        layout.addWidget(desc)

        # File storage path
        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)

        path_label = QLabel('文件存储路径：')
        path_label.setStyleSheet('font-size: 13px; font-weight: 600; color: #343a40;')
        path_label.setFixedWidth(100)
        path_layout.addWidget(path_label)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText('请选择文件存储路径...')
        self.path_edit.setStyleSheet(
            'padding: 8px 12px; border: 1px solid #ced4da;'
            'border-radius: 6px; font-size: 13px;'
        )
        path_layout.addWidget(self.path_edit)

        self.browse_btn = QPushButton('浏览...')
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 16px; border: 1px solid #ced4da;
                border-radius: 6px; font-size: 13px; color: #495057;
                background: #ffffff;
            }
            QPushButton:hover {
                background: #e9ecef; border-color: #adb5bd;
            }
        ''')
        self.browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(self.browse_btn)

        layout.addLayout(path_layout)

        hint = QLabel('提示：建议选择空闲空间较大的磁盘，系统将在此目录下按项目自动创建文件夹。')
        hint.setWordWrap(True)
        hint.setStyleSheet('font-size: 11px; color: #adb5bd; padding-left: 108px;')
        layout.addWidget(hint)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_layout.addStretch()

        self.skip_btn = QPushButton('稍后设置')
        self.skip_btn.setCursor(Qt.PointingHandCursor)
        self.skip_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 24px; border: 1px solid #ced4da;
                border-radius: 6px; font-size: 13px; color: #6c757d;
                background: transparent;
            }
            QPushButton:hover { background: #f8f9fa; }
        ''')
        self.skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.skip_btn)

        self.confirm_btn = QPushButton('确认保存')
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 24px; background: #0d6efd; color: white;
                border: none; border-radius: 6px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #0b5ed7; }
            QPushButton:disabled { background: #6c757d; }
        ''')
        self.confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(
            self, '选择文件存储路径', '',
            QFileDialog.ShowDirsOnly
        )
        if path:
            self.path_edit.setText(path)

    def _confirm(self):
        path = self.path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, '提示', '请选择文件存储路径')
            return
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception:
                QMessageBox.warning(self, '错误', f'无法创建目录：{path}')
                return
        if not os.access(path, os.W_OK):
            QMessageBox.warning(self, '错误', f'目录不可写入：{path}')
            return
        self._data_root = path
        self.accept()

    def get_data_root(self):
        return self._data_root


def check_first_run():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            if cfg.get('data_root'):
                return cfg['data_root']
        except Exception:
            pass
    return ''


def run_first_run_config():
    dlg = FirstRunConfigDialog()
    if dlg.exec() == QDialog.Accepted:
        data_root = dlg.get_data_root()
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
        return data_root
    return ''
