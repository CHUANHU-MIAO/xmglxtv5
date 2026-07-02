from flask import Flask, request, render_template, redirect, url_for
from sqlalchemy import text
from web.config import Config
from web.extensions import db, login_manager
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if app.config.get('DESKTOP_MODE'):
        os.makedirs(app.config['DESKTOP_DATA_DIR'], exist_ok=True)
        desktop_templates = os.path.join(app.config['BASEDIR'], 'desktop', 'desktop_templates')
        if os.path.isdir(desktop_templates):
            app.jinja_loader.searchpath.insert(0, desktop_templates)
    else:
        os.makedirs(os.path.join(app.config['BASEDIR'], 'instance'), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # 静态文件缓存优化（30天）
    @app.after_request
    def add_cache_header(response):
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=2592000'
        return response

    from web.models import User, EnergyFactor, Project, PettyCash

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from web.blueprints.auth import auth_bp
    from web.blueprints.projects import projects_bp
    from web.blueprints.admin import admin_bp
    from web.blueprints.files import files_bp
    from web.blueprints.estimation import estimation_bp

    @app.route('/')
    def landing():
        return render_template('landing.html')

    @app.route('/wentian')
    def wentian():
        import os
        file_path = os.path.join(app.root_path, 'templates', 'wentian.html')
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(estimation_bp)

    if app.config.get('DESKTOP_MODE'):
        @app.route('/shutdown')
        def shutdown():
            request.environ.get('werkzeug.server.shutdown')()
            return 'shutting down'

    @app.context_processor
    def inject_version():
        from flask_login import current_user
        role = current_user.role if current_user.is_authenticated else None
        return dict(system_version=app.config.get('VERSION', ''), role=role)

    with app.app_context():
        db.create_all()

        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_projects_is_valid ON projects (is_valid)'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_projects_start_date ON projects (start_date)'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects (updated_at)'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects (user_id)'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_projects_is_valid_deleted ON projects (is_valid, deleted_at)'))

        # 兼容已有数据库：添加 deleted_by / deleted_at 列
        cols = [r[1] for r in db.session.execute(text('PRAGMA table_info(projects)')).fetchall()]
        if 'deleted_by' not in cols:
            db.session.execute(text('ALTER TABLE projects ADD COLUMN deleted_by VARCHAR(80)'))
        if 'deleted_at' not in cols:
            db.session.execute(text('ALTER TABLE projects ADD COLUMN deleted_at DATETIME'))
        db.session.commit()

        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

        if app.config.get('DESKTOP_MODE'):
            _ensure_desktop_default_project()

        if not EnergyFactor.query.first():
            energy_factors = [
                {'name': '电力', 'unit': '万kWh', 'equivalent_coef': 1.229, 'equivalent_note': '当量值: 1.229 tce/万kWh', 'equivalent_coef_val': 3.015, 'equivalent_val_note': '等价值: 3.015 tce/万kWh', 'category': '能源', 'sort_order': 1},
                {'name': '天然气', 'unit': '万m³', 'equivalent_coef': 12.143, 'equivalent_note': '12.143 tce/万m³', 'equivalent_coef_val': 12.143, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 2},
                {'name': '热力', 'unit': 'GJ', 'equivalent_coef': 0.0341, 'equivalent_note': '0.0341 tce/GJ', 'equivalent_coef_val': 0.0341, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 3},
                {'name': '原煤', 'unit': 't', 'equivalent_coef': 0.7143, 'equivalent_note': '0.7143 tce/t', 'equivalent_coef_val': 0.7143, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 4},
                {'name': '洗精煤', 'unit': 't', 'equivalent_coef': 0.9000, 'equivalent_note': '0.9000 tce/t', 'equivalent_coef_val': 0.9000, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 5},
                {'name': '焦炭', 'unit': 't', 'equivalent_coef': 0.9714, 'equivalent_note': '0.9714 tce/t', 'equivalent_coef_val': 0.9714, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 6},
                {'name': '汽油', 'unit': 't', 'equivalent_coef': 1.4714, 'equivalent_note': '1.4714 tce/t', 'equivalent_coef_val': 1.4714, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 7},
                {'name': '柴油', 'unit': 't', 'equivalent_coef': 1.4571, 'equivalent_note': '1.4571 tce/t', 'equivalent_coef_val': 1.4571, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 8},
                {'name': '燃料油', 'unit': 't', 'equivalent_coef': 1.4286, 'equivalent_note': '1.4286 tce/t', 'equivalent_coef_val': 1.4286, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 9},
                {'name': '液化石油气', 'unit': 't', 'equivalent_coef': 1.7143, 'equivalent_note': '1.7143 tce/t', 'equivalent_coef_val': 1.7143, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 10},
                {'name': '炼厂干气', 'unit': 't', 'equivalent_coef': 1.5714, 'equivalent_note': '1.5714 tce/t', 'equivalent_coef_val': 1.5714, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 11},
                {'name': '煤焦油', 'unit': 't', 'equivalent_coef': 1.1429, 'equivalent_note': '1.1429 tce/t', 'equivalent_coef_val': 1.1429, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 12},
                {'name': '粗苯', 'unit': 't', 'equivalent_coef': 1.4286, 'equivalent_note': '1.4286 tce/t', 'equivalent_coef_val': 1.4286, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 13},
                {'name': '甲醇', 'unit': 't', 'equivalent_coef': 0.7143, 'equivalent_note': '0.7143 tce/t', 'equivalent_coef_val': 0.7143, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 14},
                {'name': '乙醇', 'unit': 't', 'equivalent_coef': 0.9286, 'equivalent_note': '0.9286 tce/t', 'equivalent_coef_val': 0.9286, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 15},
                {'name': '氢气', 'unit': '万m³', 'equivalent_coef': 5.0000, 'equivalent_note': '5.0000 tce/万m³', 'equivalent_coef_val': 5.0000, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 16},
                {'name': '生物质颗粒', 'unit': 't', 'equivalent_coef': 0.5000, 'equivalent_note': '0.5000 tce/t', 'equivalent_coef_val': 0.5000, 'equivalent_val_note': '', 'category': '能源', 'sort_order': 17},
                {'name': '除盐水', 'unit': 't', 'equivalent_coef': 0.0000, 'equivalent_note': '', 'equivalent_coef_val': 0.0980, 'equivalent_val_note': '等价值: 0.0980 tce/t', 'category': '耗能工质', 'sort_order': 18},
                {'name': '压缩空气', 'unit': '万m³', 'equivalent_coef': 0.0000, 'equivalent_note': '', 'equivalent_coef_val': 0.4000, 'equivalent_val_note': '等价值: 0.4000 tce/万m³', 'category': '耗能工质', 'sort_order': 19},
                {'name': '氧气', 'unit': '万m³', 'equivalent_coef': 0.0000, 'equivalent_note': '', 'equivalent_coef_val': 0.4000, 'equivalent_val_note': '等价值: 0.4000 tce/万m³', 'category': '耗能工质', 'sort_order': 20},
                {'name': '氮气', 'unit': '万m³', 'equivalent_coef': 0.0000, 'equivalent_note': '', 'equivalent_coef_val': 0.2000, 'equivalent_val_note': '等价值: 0.2000 tce/万m³', 'category': '耗能工质', 'sort_order': 21},
                {'name': '水', 'unit': 't', 'equivalent_coef': 0.0000, 'equivalent_note': '', 'equivalent_coef_val': 0.0857, 'equivalent_val_note': '等价值: 0.0857 tce/t', 'category': '耗能工质', 'sort_order': 22},
            ]
            for ef in energy_factors:
                factor = EnergyFactor(
                    name=ef['name'],
                    unit=ef['unit'],
                    equivalent_coef=ef['equivalent_coef'],
                    equivalent_note=ef['equivalent_note'],
                    equivalent_coef_val=ef['equivalent_coef_val'],
                    equivalent_val_note=ef['equivalent_val_note'],
                    category=ef['category'],
                    sort_order=ef['sort_order'],
                )
                db.session.add(factor)
            db.session.commit()

    return app


def _ensure_desktop_default_project():
    from web.models import User, Project
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        return
    default = Project.query.filter_by(name='桌面测算项目').first()
    if not default:
        default = Project(
            name='桌面测算项目',
            description='桌面端默认测算项目',
            user_id=admin.id,
            author='admin',
        )
        db.session.add(default)
        db.session.commit()
