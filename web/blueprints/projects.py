import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from web.models import Project, User
from web.extensions import db

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/')
@login_required
def index():
    projects = Project.query.filter_by(is_valid=1).order_by(Project.updated_at.desc()).all()
    return render_template('index.html', projects=projects)


@projects_bp.route('/my_projects')
@login_required
def my_projects():
    if current_user.role == 'admin':
        projects = Project.query.filter_by(is_valid=1).order_by(Project.updated_at.desc()).all()
    else:
        projects = Project.query.filter_by(user_id=current_user.id, is_valid=1).order_by(Project.updated_at.desc()).all()
    return render_template('my_projects.html', projects=projects)


@projects_bp.route('/project/add', methods=['GET', 'POST'])
@login_required
def project_add():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')
        project_type = request.form.get('project_type')
        phase = request.form.get('phase')
        project = Project(
            name=name,
            description=description,
            location=location,
            project_type=project_type,
            phase=phase,
            user_id=current_user.id,
            author=current_user.username,
            progress='新建'
        )
        db.session.add(project)
        db.session.commit()
        flash('项目创建成功')
        return redirect(url_for('projects.my_projects'))
    return render_template('project_add.html')


@projects_bp.route('/project/detail/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)


@projects_bp.route('/project/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def project_edit(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == 'POST':
        project.name = request.form.get('name')
        project.description = request.form.get('description')
        project.location = request.form.get('location')
        project.project_type = request.form.get('project_type')
        project.phase = request.form.get('phase')
        project.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        flash('项目更新成功')
        return redirect(url_for('projects.project_detail', project_id=project.id))
    return render_template('project_edit.html', project=project)


@projects_bp.route('/project/delete/<int:project_id>')
@login_required
def project_delete(project_id):
    project = Project.query.get_or_404(project_id)
    project.is_valid = 0
    db.session.commit()
    flash('项目已删除')
    return redirect(url_for('projects.my_projects'))
