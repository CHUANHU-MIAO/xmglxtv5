from flask import Blueprint, request, jsonify
from models import db
from services.auth_service import create_user, login_user, create_token, verify_token, bind_device, unbind_device, get_user_devices
from services.subscription_service import get_user_subscription, check_subscription_valid
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码必填'}), 400
    user, msg = create_user(username, password, email)
    if user:
        return jsonify({'success': True, 'message': msg})
    else:
        return jsonify({'success': False, 'message': msg}), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    device_id = data.get('device_id')
    device_name = data.get('device_name') or '未知设备'
    if not username or not password or not device_id:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    user, msg = login_user(username, password)
    if not user:
        return jsonify({'success': False, 'message': msg}), 401
    device, ok, bind_msg = bind_device(user, device_id, device_name)
    if not ok:
        return jsonify({'success': False, 'message': bind_msg, 'need_unbind': True, 'devices': [{'id': d.id, 'device_id': d.device_id, 'device_name': d.device_name} for d in get_user_devices(user)]}), 400
    token = create_token(user.id)
    sub = get_user_subscription(user)
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'subscription': {
                'level': sub.level,
                'max_projects': sub.max_projects,
                'expire_date': sub.expire_date.isoformat() if sub.expire_date else None
            }
        }
    })

@auth_bp.route('/verify', methods=['POST'])
def verify():
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({'valid': False}), 401
    user = verify_token(token)
    if not user:
        return jsonify({'valid': False}), 401
    sub = get_user_subscription(user)
    return jsonify({
        'valid': True,
        'user': {'id': user.id, 'username': user.username},
        'subscription': {
            'level': sub.level,
            'max_projects': sub.max_projects,
            'expire_date': sub.expire_date.isoformat() if sub.expire_date else None
        }
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'success': True, 'message': '登出成功'})
