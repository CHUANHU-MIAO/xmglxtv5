import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from web.extensions import db


visitor_projects = db.Table('visitor_projects',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='engineer')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_active_time = db.Column(db.DateTime, nullable=True)

    visitor_projects_rel = db.relationship('Project', secondary=visitor_projects,
                                           backref=db.backref('visitors', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    project_type = db.Column(db.String(100))
    phase = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author = db.Column(db.String(80))
    progress = db.Column(db.String(50))
    is_valid = db.Column(db.Integer, default=1)

    start_date = db.Column(db.Date, nullable=True)
    owner = db.Column(db.String(200), nullable=True)
    total_investment = db.Column(db.Float, nullable=True)
    contract_amount = db.Column(db.Float, nullable=True)
    contract_status = db.Column(db.String(50), nullable=True)
    invoice_status = db.Column(db.String(50), nullable=True)
    invoiced_amount = db.Column(db.Float, nullable=True)
    payment_status = db.Column(db.String(50), nullable=True)
    settled_amount = db.Column(db.Float, nullable=True)
    payment_settlement_status = db.Column(db.String(50), nullable=True)
    source = db.Column(db.String(100), nullable=True)
    owner_name = db.Column(db.String(100), nullable=True)
    owner_phone = db.Column(db.String(20), nullable=True)
    service_content = db.Column(db.Text, nullable=True)
    remark = db.Column(db.Text, nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    creator = db.relationship('User', backref=db.backref('projects', lazy='dynamic'))
    attachments = db.relationship('Attachment', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def engineer(self):
        return self.creator


class Attachment(db.Model):
    __tablename__ = 'attachments'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    save_name = db.Column(db.String(200), nullable=False)
    file_type = db.Column(db.String(50))
    upload_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    upload_user = db.Column(db.String(50))


class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer)
    user = db.Column(db.String(50))
    content = db.Column(db.Text)
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class StandardFile(db.Model):
    __tablename__ = 'standard_files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    standard_name = db.Column(db.String(200), nullable=False)
    version = db.Column(db.String(50), default='1.0')
    file_type = db.Column(db.String(50), default='建设标准')
    file_path = db.Column(db.String(500), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    upload_user = db.Column(db.String(50))
    download_count = db.Column(db.Integer, default=0)


class FundRecord(db.Model):
    __tablename__ = 'fund_records'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(100), nullable=False)
    remark = db.Column(db.Text)
    use_date = db.Column(db.Date, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    create_user = db.Column(db.String(50))
    expense_type = db.Column(db.String(20), default='运营支出')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    project = db.relationship('Project', backref=db.backref('fund_records', lazy='dynamic'))


class PettyCash(db.Model):
    """备用金记录 — 仅做记录，不参与计算"""
    __tablename__ = 'petty_cash'
    id = db.Column(db.Integer, primary_key=True)
    received_time = db.Column(db.DateTime, nullable=False)
    method = db.Column(db.String(20), nullable=False)  # 微信 / 现金 / 银行卡
    amount = db.Column(db.Float, nullable=False)
    remark = db.Column(db.Text)
    create_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    create_user = db.Column(db.String(50))


class EnergyFactor(db.Model):
    __tablename__ = 'energy_factors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    unit = db.Column(db.String(50), nullable=False)
    equivalent_coef = db.Column(db.Float, nullable=False)
    equivalent_note = db.Column(db.String(200))
    equivalent_coef_val = db.Column(db.Float, default=0)
    equivalent_val_note = db.Column(db.String(200))
    category = db.Column(db.String(50), default='能源')
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class InvestmentData(db.Model):
    __tablename__ = 'investment_data'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    serial_number = db.Column(db.String(20), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    building_cost = db.Column(db.Float, default=0)
    installation_cost = db.Column(db.Float, default=0)
    equipment_cost = db.Column(db.Float, default=0)
    other_cost = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20), nullable=True)
    quantity = db.Column(db.Float, default=0)
    index = db.Column(db.Float, default=0)
    use_index = db.Column(db.Boolean, default=False)
    billing_basis = db.Column(db.String(200), nullable=True)
    calc_rate = db.Column(db.Float, default=0)
    discount_rate = db.Column(db.Float, default=100)
    build_category = db.Column(db.String(50), nullable=True)
    address_category = db.Column(db.String(50), nullable=True)
    is_reserve_rate = db.Column(db.Boolean, default=False)
    reserve_rate = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    project = db.relationship('Project', backref=db.backref('investment_data', lazy='dynamic'))
