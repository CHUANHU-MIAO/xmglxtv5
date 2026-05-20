import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from web.models import Project
from web.extensions import db

files_bp = Blueprint('files', __name__, url_prefix='/files')


@files_bp.route('/<int:project_id>')
@login_required
def file_viewer(project_id):
    project = Project.query.get_or_404(project_id)
    upload_folder = current_app.config['UPLOAD_FOLDER']
    project_folder = os.path.join(upload_folder, str(project_id))
    files_list = []
    if os.path.exists(project_folder):
        for f in os.listdir(project_folder):
            filepath = os.path.join(project_folder, f)
            if os.path.isfile(filepath):
                files_list.append({
                    'name': f,
                    'size': os.path.getsize(filepath),
                    'mtime': os.path.getmtime(filepath)
                })
    return render_template('file_viewer.html', project=project, files=files_list)


@files_bp.route('/upload/<int:project_id>', methods=['POST'])
@login_required
def upload(project_id):
    project = Project.query.get_or_404(project_id)
    if 'file' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('files.file_viewer', project_id=project_id))
    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件')
        return redirect(url_for('files.file_viewer', project_id=project_id))
    if file:
        filename = secure_filename(file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        project_folder = os.path.join(upload_folder, str(project_id))
        os.makedirs(project_folder, exist_ok=True)
        file.save(os.path.join(project_folder, filename))
        flash('文件上传成功')
    return redirect(url_for('files.file_viewer', project_id=project_id))


@files_bp.route('/download/<int:project_id>/<filename>')
@login_required
def download(project_id, filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    project_folder = os.path.join(upload_folder, str(project_id))
    return send_from_directory(project_folder, filename, as_attachment=True)


@files_bp.route('/delete/<int:project_id>/<filename>')
@login_required
def delete(project_id, filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    project_folder = os.path.join(upload_folder, str(project_id))
    filepath = os.path.join(project_folder, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash('文件已删除')
    return redirect(url_for('files.file_viewer', project_id=project_id))
