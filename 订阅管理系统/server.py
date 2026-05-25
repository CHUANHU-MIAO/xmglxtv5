import functools
import os
from flask import Flask, jsonify, render_template, session, redirect, request
from config import Config
from models import db
from routes.auth import auth_bp
from routes.subscription import sub_bp
from routes.device import device_bp
from routes.admin import admin_bp
from routes.pair import pair_bp

app = Flask(__name__)
app.config.from_object(Config)
app.config['SESSION_TYPE'] = 'filesystem'
db.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(sub_bp, url_prefix='/api/subscription')
app.register_blueprint(device_bp, url_prefix='/api/device')
app.register_blueprint(admin_bp, url_prefix='/admin/api')
app.register_blueprint(pair_bp, url_prefix='/api/pair')

def admin_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin/login')
        return view(**kwargs)
    return wrapped

@app.route('/')
def index():
    return redirect('/admin/login')


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')


@app.route('/pricing')
def pricing_page():
    return render_template('pricing.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin/dashboard')
        return render_template('admin_login.html', error='用户名或密码错误')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

@app.route('/scan')
def scan_page():
    return render_template('scan.html')

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/admin/') and not request.path.startswith('/admin/api/'):
        return redirect('/admin/dashboard')
    return jsonify({'success': False, 'message': '接口不存在'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'message': '服务器内部错误'}), 500

def init_db():
    with app.app_context():
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)
