import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.energy.calculator import (
    calculate_energy_item_tce, calculate_total_energy,
    calculate_energy_benchmarks, calculate_electricity_load,
)
from core.energy.factors import ENERGY_FACTORS, get_factor, list_factors
from core.finance.calculator import (
    calculate_debt_service_schedule, calculate_npv, calculate_irr,
    calculate_payback_period, calculate_coverage_ratio,
    calculate_total_debt_service, calculate_revenue_projection,
    calculate_profit,
)
from core.investment.calculator import (
    calculate_all as calc_investment_all,
    calculate_project_management_fee, calculate_design_fee,
    calculate_survey_fee, calculate_construction_prep_fee,
    calculate_consultation_fee, calculate_drawing_review_fee,
    calculate_cost_consulting_fee, calculate_bidding_agent_fee,
    calculate_supervision_fee, calculate_insurance_fee,
    calculate_final_settlement_fee, calculate_infrastructure_fee,
    calculate_air_defense_fee,
)

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
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

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


class LoginDialog(QDialog):
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle('用户登录')
        self.setFixedSize(380, 260)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel('项目管理系统')
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText('请输入用户名')
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText('请输入密码')
        self.password_edit.setEchoMode(QLineEdit.Password)
        form.addRow('用户名：', self.username_edit)
        form.addRow('密　码：', self.password_edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton('登 录')
        self.login_btn.setDefault(True)
        self.register_btn = QPushButton('注 册')
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        layout.addLayout(btn_layout)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('color: red;')
        layout.addWidget(self.status_label)

        self.login_btn.clicked.connect(self._on_login)
        self.register_btn.clicked.connect(self._on_register)
        self.password_edit.returnPressed.connect(self._on_login)

    def _on_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            self.status_label.setText('请输入用户名和密码')
            return
        self.login_btn.setEnabled(False)
        self.status_label.setText('正在登录...')
        self.status_label.setStyleSheet('color: blue;')
        QApplication.processEvents()
        ok, msg = self.client.login(username, password)
        if ok:
            self.accept()
        else:
            self.status_label.setText(msg)
            self.status_label.setStyleSheet('color: red;')
            self.login_btn.setEnabled(True)

    def _on_register(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            self.status_label.setText('请输入用户名和密码')
            return
        self.register_btn.setEnabled(False)
        self.status_label.setText('正在注册...')
        self.status_label.setStyleSheet('color: blue;')
        QApplication.processEvents()
        try:
            resp = requests.post(
                f'{self.client.server_url}/api/auth/register',
                json={'username': username, 'password': password},
                timeout=10,
            )
            data = resp.json()
            if data.get('success'):
                self.status_label.setText('注册成功，请登录')
                self.status_label.setStyleSheet('color: green;')
            else:
                self.status_label.setText(data.get('message', '注册失败'))
                self.status_label.setStyleSheet('color: red;')
        except Exception as e:
            self.status_label.setText(f'注册时发生错误：{str(e)}')
            self.status_label.setStyleSheet('color: red;')
        self.register_btn.setEnabled(True)


class InvestmentTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.engineering_total = QDoubleSpinBox()
        self.engineering_total.setRange(0, 1e12)
        self.engineering_total.setDecimals(2)
        self.engineering_total.setSuffix(' 元')
        self.engineering_total.setValue(50000000)
        form.addRow('工程费用：', self.engineering_total)
        self.building_area = QDoubleSpinBox()
        self.building_area.setRange(0, 1e9)
        self.building_area.setDecimals(2)
        self.building_area.setSuffix(' ㎡')
        self.building_area.setValue(10000)
        form.addRow('建筑面积：', self.building_area)
        layout.addLayout(form)
        self.calc_btn = QPushButton('计算投资估算')
        layout.addWidget(self.calc_btn)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(['费用项目', '金额（元）'])
        layout.addWidget(self.result_table)
        self.calc_btn.clicked.connect(self._calculate)

    def _calculate(self):
        eng = self.engineering_total.value()
        area = self.building_area.value()
        results = calc_investment_all(eng, area)
        items = [
            ('项目管理费', results['project_management_fee']),
            ('设计费', results['design_fee']),
            ('勘察费', results['survey_fee']),
            ('建设准备费', results['construction_prep_fee']),
            ('咨询费', results['consultation_fee']),
            ('图纸审查费', results['drawing_review_fee']),
            ('造价咨询费', results['cost_consulting_fee']),
            ('招标代理费', results['bidding_agent_fee']),
            ('监理费', results['supervision_fee']),
            ('保险费', results['insurance_fee']),
            ('竣工结算费', results['final_settlement_fee']),
            ('基础设施费', results['infrastructure_fee']),
            ('人防费', results['air_defense_fee']),
        ]
        total = sum(v for _, v in items)
        items.append(('合计', total))
        self.result_table.setRowCount(len(items))
        for i, (name, val) in enumerate(items):
            self.result_table.setItem(i, 0, QTableWidgetItem(name))
            self.result_table.setItem(i, 1, QTableWidgetItem(f'{val:,.2f}'))
        self.result_table.resizeColumnsToContents()


class EnergyTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        top_form = QFormLayout()
        self.energy_combo = QComboBox()
        self.energy_combo.addItems(list_factors())
        top_form.addRow('能源类型：', self.energy_combo)
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0, 1e12)
        self.qty_spin.setDecimals(4)
        self.qty_spin.setValue(100)
        top_form.addRow('年用量：', self.qty_spin)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 1e6)
        self.price_spin.setDecimals(4)
        self.price_spin.setValue(0.8)
        top_form.addRow('单价（元/单位）：', self.price_spin)
        self.include_check = QCheckBox('计入综合能耗')
        self.include_check.setChecked(True)
        top_form.addRow('', self.include_check)
        self.add_btn = QPushButton('添加能源项')
        top_form.addRow('', self.add_btn)
        layout.addLayout(top_form)
        self.energy_table = QTableWidget()
        self.energy_table.setColumnCount(5)
        self.energy_table.setHorizontalHeaderLabels(['能源名称', '年用量', '当量值(tce)', '等价值(tce)', '年费用(万元)'])
        layout.addWidget(self.energy_table)
        self.calc_btn = QPushButton('计算能耗合计')
        layout.addWidget(self.calc_btn)
        self.result_label = QLabel('')
        layout.addWidget(self.result_label)
        self.elec_group = QGroupBox('电力负荷计算')
        elec_layout = QFormLayout()
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0, 1e6)
        self.density_spin.setValue(50)
        elec_layout.addRow('负荷密度(W/㎡)：', self.density_spin)
        self.density_qty = QDoubleSpinBox()
        self.density_qty.setRange(0, 1e9)
        self.density_qty.setValue(1000)
        elec_layout.addRow('面积(㎡)：', self.density_qty)
        self.kc_spin = QDoubleSpinBox()
        self.kc_spin.setRange(0, 1)
        self.kc_spin.setDecimals(4)
        self.kc_spin.setValue(0.75)
        elec_layout.addRow('需要系数Kc：', self.kc_spin)
        self.cos_phi = QDoubleSpinBox()
        self.cos_phi.setRange(0, 1)
        self.cos_phi.setDecimals(4)
        self.cos_phi.setValue(0.9)
        elec_layout.addRow('功率因数cosφ：', self.cos_phi)
        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0, 8760)
        self.hours_spin.setValue(2190)
        elec_layout.addRow('年工作时数(h)：', self.hours_spin)
        self.elec_calc_btn = QPushButton('计算电力负荷')
        elec_layout.addRow('', self.elec_calc_btn)
        self.elec_result = QLabel('')
        elec_layout.addRow('', self.elec_result)
        self.elec_group.setLayout(elec_layout)
        layout.addWidget(self.elec_group)
        self.energy_items = []
        self.add_btn.clicked.connect(self._add_energy_item)
        self.calc_btn.clicked.connect(self._calculate_total)
        self.elec_calc_btn.clicked.connect(self._calculate_electricity)

    def _add_energy_item(self):
        name = self.energy_combo.currentText()
        qty = self.qty_spin.value()
        price = self.price_spin.value()
        include = self.include_check.isChecked()
        factor = get_factor(name)
        if factor:
            eq_coef = factor['equivalent_coef']
            ev_coef = factor.get('equivalent_coef_val', 0)
        else:
            eq_coef = 0
            ev_coef = 0
        eq_tce, ev_tce = calculate_energy_item_tce(name, qty, eq_coef, ev_coef)
        cost = qty * price / 10000
        row = self.energy_table.rowCount()
        self.energy_table.insertRow(row)
        self.energy_table.setItem(row, 0, QTableWidgetItem(name))
        self.energy_table.setItem(row, 1, QTableWidgetItem(f'{qty:.4f}'))
        self.energy_table.setItem(row, 2, QTableWidgetItem(f'{eq_tce:.4f}'))
        self.energy_table.setItem(row, 3, QTableWidgetItem(f'{ev_tce:.4f}'))
        self.energy_table.setItem(row, 4, QTableWidgetItem(f'{cost:.4f}'))
        self.energy_items.append({
            'name': name,
            'annual_qty': qty,
            'equivalent_coef': eq_coef,
            'equivalent_coef_val': ev_coef,
            'unit_price': price,
            'include_in_total': include,
        })
        self.energy_table.resizeColumnsToContents()

    def _calculate_total(self):
        if not self.energy_items:
            QMessageBox.information(self, '提示', '请先添加能源项')
            return
        total_eq, total_ev, total_cost = calculate_total_energy(self.energy_items)
        self.result_label.setText(
            f'综合能耗（当量值）: {total_eq:.4f} tce  |  '
            f'综合能耗（等价值）: {total_ev:.4f} tce  |  '
            f'年总费用: {total_cost:.4f} 万元'
        )

    def _calculate_electricity(self):
        density = self.density_spin.value()
        density_qty = self.density_qty.value()
        kc = self.kc_spin.value()
        cos_phi = self.cos_phi.value()
        hours = self.hours_spin.value()
        result = calculate_electricity_load(density, density_qty, kc, cos_phi, hours)
        self.elec_result.setText(
            f'有功功率: {result["active_kw"]:.2f} kW  |  '
            f'无功功率: {result["reactive_kvar"]:.2f} kVar  |  '
            f'视在功率: {result["apparent_kva"]:.2f} kVA  |  '
            f'年用电量: {result["power_consumption"]:.2f} kWh'
        )


class FinanceTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.principal_spin = QDoubleSpinBox()
        self.principal_spin.setRange(0, 1e12)
        self.principal_spin.setDecimals(2)
        self.principal_spin.setValue(10000)
        self.principal_spin.setSuffix(' 元')
        form.addRow('贷款本金：', self.principal_spin)
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 1)
        self.rate_spin.setDecimals(4)
        self.rate_spin.setValue(0.05)
        self.rate_spin.setSuffix(' (5%)')
        form.addRow('年利率：', self.rate_spin)
        self.years_spin = QDoubleSpinBox()
        self.years_spin.setRange(1, 100)
        self.years_spin.setDecimals(0)
        self.years_spin.setValue(10)
        self.years_spin.setSuffix(' 年')
        form.addRow('贷款年限：', self.years_spin)
        self.method_combo = QComboBox()
        self.method_combo.addItems(['等额本金', '等额本息', '到期一次还本'])
        form.addRow('还款方式：', self.method_combo)
        self.start_year_spin = QDoubleSpinBox()
        self.start_year_spin.setRange(2000, 2100)
        self.start_year_spin.setDecimals(0)
        self.start_year_spin.setValue(2024)
        form.addRow('起始年份：', self.start_year_spin)
        self.debt_btn = QPushButton('计算还本付息')
        form.addRow('', self.debt_btn)
        layout.addLayout(form)
        self.debt_table = QTableWidget()
        self.debt_table.setColumnCount(5)
        self.debt_table.setHorizontalHeaderLabels(['年份', '还本(元)', '付息(元)', '合计(元)', '剩余本金(元)'])
        layout.addWidget(self.debt_table)
        self.debt_summary = QLabel('')
        layout.addWidget(self.debt_summary)
        npv_group = QGroupBox('NPV/IRR计算')
        npv_layout = QFormLayout()
        self.cash_flow_edit = QLineEdit()
        self.cash_flow_edit.setPlaceholderText('例如：-10000,3000,4000,5000,2000')
        npv_layout.addRow('现金流(逗号分隔)：', self.cash_flow_edit)
        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, 1)
        self.discount_spin.setDecimals(4)
        self.discount_spin.setValue(0.08)
        npv_layout.addRow('折现率：', self.discount_spin)
        self.npv_btn = QPushButton('计算NPV/IRR')
        npv_layout.addRow('', self.npv_btn)
        self.npv_result = QLabel('')
        npv_layout.addRow('', self.npv_result)
        npv_group.setLayout(npv_layout)
        layout.addWidget(npv_group)
        self.debt_btn.clicked.connect(self._calculate_debt)
        self.npv_btn.clicked.connect(self._calculate_npv_irr)

    def _calculate_debt(self):
        principal = self.principal_spin.value()
        rate = self.rate_spin.value()
        years = int(self.years_spin.value())
        start_year = int(self.start_year_spin.value())
        method_map = {
            '等额本金': 'equal-principal',
            '等额本息': 'equal-installment',
            '到期一次还本': 'lump-sum',
        }
        method = method_map.get(self.method_combo.currentText(), 'equal-principal')
        schedule = calculate_debt_service_schedule(principal, rate, years, start_year, method)
        self.debt_table.setRowCount(len(schedule))
        for i, item in enumerate(schedule):
            self.debt_table.setItem(i, 0, QTableWidgetItem(str(item['year'])))
            self.debt_table.setItem(i, 1, QTableWidgetItem(f'{item["principal"]:,.2f}'))
            self.debt_table.setItem(i, 2, QTableWidgetItem(f'{item["interest"]:,.2f}'))
            self.debt_table.setItem(i, 3, QTableWidgetItem(f'{item["total"]:,.2f}'))
            self.debt_table.setItem(i, 4, QTableWidgetItem(f'{item["remaining"]:,.2f}'))
        self.debt_table.resizeColumnsToContents()
        tp, ti, tt = calculate_total_debt_service(schedule)
        self.debt_summary.setText(
            f'还本合计: {tp:,.2f} 元  |  付息合计: {ti:,.2f} 元  |  '
            f'本息合计: {tt:,.2f} 元'
        )

    def _calculate_npv_irr(self):
        text = self.cash_flow_edit.text().strip()
        if not text:
            QMessageBox.information(self, '提示', '请输入现金流')
            return
        try:
            cash_flows = [float(x.strip()) for x in text.split(',')]
        except ValueError:
            QMessageBox.warning(self, '错误', '现金流格式错误，请用逗号分隔数字')
            return
        discount = self.discount_spin.value()
        npv = calculate_npv(cash_flows, discount)
        irr = calculate_irr(cash_flows)
        payback = calculate_payback_period(cash_flows)
        result = f'NPV: {npv:,.2f} 元  |  IRR: {irr*100:.2f}%  |  回收期: '
        if payback is not None:
            result += f'{payback:.2f} 年'
        else:
            result += '无法回收'
        self.npv_result.setText(result)


class MainWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowTitle('项目管理系统 - 桌面端')
        self.resize(900, 700)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        user_info = self.client.user_info or {}
        username = user_info.get('username', '未知用户') if isinstance(user_info, dict) else '未知用户'
        header = QLabel(f'欢迎使用，{username}')
        header_font = QFont()
        header_font.setPointSize(12)
        header.setFont(header_font)
        layout.addWidget(header)
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(InvestmentTab(), '投资估算')
        self.tab_widget.addTab(EnergyTab(), '能耗测算')
        self.tab_widget.addTab(FinanceTab(), '财务测算')
        layout.addWidget(self.tab_widget)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.logout_btn = QPushButton('退出登录')
        self.logout_btn.clicked.connect(self._on_logout)
        btn_layout.addWidget(self.logout_btn)
        layout.addLayout(btn_layout)

    def _on_logout(self):
        reply = QMessageBox.question(
            self, '确认退出', '确定要退出登录吗？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.client.logout()
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('项目管理系统')
    client = SubscriptionClient()
    ok, msg = client.verify()
    if not ok:
        dialog = LoginDialog(client)
        if dialog.exec_() != QDialog.Accepted:
            sys.exit(0)
    window = MainWindow(client)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()