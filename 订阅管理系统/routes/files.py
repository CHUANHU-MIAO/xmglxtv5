import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from models import db, CommonFile
from services.auth_service import verify_token

files_bp = Blueprint('files', __name__)


def get_upload_folder():
    folder = os.path.join(current_app.root_path, 'uploads', 'common_files')
    os.makedirs(folder, exist_ok=True)
    return folder


def get_user_from_token():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.args.get('token', '')
    if not token:
        return None
    return verify_token(token)


@files_bp.route('/list', methods=['GET'])
def list_files():
    user = get_user_from_token()
    if not user:
        return jsonify({'success': False, 'message': '未登录或登录已过期'}), 401
    files = CommonFile.query.filter_by(user_id=user.id).order_by(CommonFile.upload_time.desc()).all()
    return jsonify({
        'success': True,
        'files': [{
            'id': f.id,
            'filename': f.filename,
            'file_size': f.file_size,
            'upload_time': f.upload_time.strftime('%Y-%m-%d %H:%M')
        } for f in files]
    })


@files_bp.route('/upload', methods=['POST'])
def upload_file():
    user = get_user_from_token()
    if not user:
        return jsonify({'success': False, 'message': '未登录或登录已过期'}), 401
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '请选择文件'}), 400
    ext = os.path.splitext(file.filename)[1]
    save_name = f"{uuid.uuid4().hex}{ext}"
    user_folder = os.path.join(get_upload_folder(), str(user.id))
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, save_name)
    file.save(file_path)
    file_size = os.path.getsize(file_path)
    cf = CommonFile(
        user_id=user.id,
        filename=file.filename,
        save_name=save_name,
        file_size=file_size,
    )
    db.session.add(cf)
    db.session.commit()
    return jsonify({'success': True, 'message': '上传成功', 'file': {'id': cf.id, 'filename': cf.filename}})


@files_bp.route('/download/<int:file_id>', methods=['GET'])
def download_file(file_id):
    user = get_user_from_token()
    if not user:
        return jsonify({'success': False, 'message': '未登录或登录已过期'}), 401
    cf = CommonFile.query.get_or_404(file_id)
    if cf.user_id != user.id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    user_folder = os.path.join(get_upload_folder(), str(user.id))
    return send_from_directory(user_folder, cf.save_name, as_attachment=True, download_name=cf.filename)


@files_bp.route('/delete/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    user = get_user_from_token()
    if not user:
        return jsonify({'success': False, 'message': '未登录或登录已过期'}), 401
    cf = CommonFile.query.get_or_404(file_id)
    if cf.user_id != user.id:
        return jsonify({'success': False, 'message': '无权操作'}), 403
    user_folder = os.path.join(get_upload_folder(), str(user.id))
    file_path = os.path.join(user_folder, cf.save_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(cf)
    db.session.commit()
    return jsonify({'success': True, 'message': '删除成功'})
