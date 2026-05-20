from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from web.models import User, Project
from web.extensions import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('需要管理员权限')
            return redirect(url_for('projects.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users_list = User.query.all()
    return render_template('admin_users.html', users=users_list)


@admin_bp.route('/projects')
@login_required
@admin_required
def projects():
    projects_list = Project.query.order_by(Project.updated_at.desc()).all()
    return render_template('admin_projects.html', projects=projects_list)


@admin_bp.route('/user/delete/<int:user_id>')
@login_required
@admin_required
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('不能删除自己')
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    flash('用户已删除')
    return redirect(url_for('admin.users'))


@admin_bp.route('/project/delete/<int:project_id>')
@login_required
@admin_required
def project_delete(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash('项目已删除')
    return redirect(url_for('admin.projects'))


@admin_bp.route('/operations')
@login_required
@admin_required
def operations():
    return render_template('admin_operations.html')


@admin_bp.route('/database')
@login_required
@admin_required
def database():
    return render_template('database.html')
