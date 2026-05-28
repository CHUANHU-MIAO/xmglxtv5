from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from web.models import User
from web.extensions import db
import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            user.last_active_time = datetime.datetime.utcnow()
            db.session.commit()
            return redirect('/home')
        flash('用户名或密码错误')
    else:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=365)
        inactive_visitors = User.query.filter(
            User.role == 'visitor',
            User.last_active_time < cutoff
        ).all()
        for v in inactive_visitors:
            db.session.delete(v)
        if inactive_visitors:
            db.session.commit()
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return redirect(url_for('auth.register'))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录')
        return redirect(url_for('auth.login'))
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pw = request.form.get('old_password')
        new_pw = request.form.get('new_password')
        if current_user.check_password(old_pw):
            current_user.set_password(new_pw)
            db.session.commit()
            flash('密码修改成功')
            return redirect('/home')
        flash('原密码错误')
    return render_template('change_password.html', role=current_user.role)
