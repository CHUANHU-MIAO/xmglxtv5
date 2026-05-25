import re
from flask import Blueprint, request, jsonify
from models import db
from services.auth_service import (
    create_user, login_user, create_token, verify_token,
    bind_device, unbind_device, get_user_devices,
    check_unique, forgot_password_verify, verify_and_reset_password
)
from services.subscription_service import get_user_subscription, check_subscription_valid
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


def check_email(email):
    return re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email) is not None


def check_phone(phone):
    return re.match(r'^1\d{10}$', phone) is not None


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '').strip() or None
    phone = data.get('phone', '').strip() or None
    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码必填'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码长度不能少于6位'}), 400
    if email and not check_email(email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
    if phone and not check_phone(phone):
        return jsonify({'success': False, 'message': '手机号格式不正确'}), 400
    user, msg = create_user(username, password, email, phone)
    if user:
        return jsonify({'success': True, 'message': msg, 'user': {'id': user.id, 'username': user.username}})
    else:
        return jsonify({'success': False, 'message': msg}), 400


@auth_bp.route('/check-unique', methods=['POST'])
def check_unique_api():
    data = request.get_json()
    username = data.get('username', '').strip() or None
    email = data.get('email', '').strip() or None
    phone = data.get('phone', '').strip() or None
    dup = check_unique(username=username, email=email, phone=phone)
    if dup:
        field_map = {'username': '用户名', 'email': '邮箱', 'phone': '手机号'}
        return jsonify({'success': False, 'field': dup, 'message': f'{field_map.get(dup, dup)}已被注册'})
    return jsonify({'success': True, 'message': '均可使用'})


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    username = data.get('username', '').strip()
    if not username:
        return jsonify({'success': False, 'message': '请输入用户名'}), 400
    result, err = forgot_password_verify(username)
    if err:
        return jsonify({'success': False, 'message': err}), 404
    return jsonify({'success': True, 'data': result})


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    username = data.get('username', '').strip()
    verify_methods = data.get('verify_methods', [])
    new_password = data.get('new_password', '')
    if not username or not new_password:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码长度不能少于6位'}), 400
    ok, msg = verify_and_reset_password(username, verify_methods, new_password)
    if ok:
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
