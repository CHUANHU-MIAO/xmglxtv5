from flask import Blueprint, request, jsonify
from config import Config
from models import db, User, Subscription, Device, PaymentRecord
from services.auth_service import hash_password
from services.subscription_service import create_subscription_for_admin
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def check_admin(username, password):
    return username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD

@admin_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not check_admin(username, password):
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
    return jsonify({'success': True, 'message': '登录成功'})

@admin_bp.route('/users', methods=['GET'])
def users():
    users = User.query.all()
    result = []
    for u in users:
        sub = Subscription.query.filter_by(user_id=u.id, status='active').order_by(Subscription.id.desc()).first()
        result.append({
            'id': u.id, 'username': u.username, 'email': u.email, 'phone': u.phone,
            'status': u.status, 'created_at': u.created_at.isoformat(),
            'subscription': {
                'level': sub.level,
                'max_projects': sub.max_projects,
                'expire_date': sub.expire_date.isoformat() if sub.expire_date else None
            } if sub else None,
        })
    return jsonify({'success': True, 'users': result})

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
def user_detail(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    sub = Subscription.query.filter_by(user_id=user.id, status='active').order_by(Subscription.id.desc()).first()
    devices = Device.query.filter_by(user_id=user.id, is_active=True).all()
    return jsonify({
        'success': True,
        'user': {
            'id': user.id, 'username': user.username, 'email': user.email,
            'subscription': {'level': sub.level, 'expire_date': sub.expire_date.isoformat() if sub and sub.expire_date else None} if sub else None,
            'devices': [{'id': d.id, 'device_name': d.device_name, 'last_login': d.last_login.isoformat()} for d in devices]
        }
    })

@admin_bp.route('/users', methods=['POST'])
def create_user_admin():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if not username or not password:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    existing = User.query.filter_by(username=username).first()
    if existing:
        return jsonify({'success': False, 'message': '用户名已存在'}), 400
    user = User(username=username, password_hash=hash_password(password), email=email)
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'message': '用户创建成功', 'user': {'id': user.id}})

@admin_bp.route('/users/<int:user_id>/subscription', methods=['POST'])
def set_subscription():
    data = request.get_json()
    level = data.get('level')
    expire_str = data.get('expire_date')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    expire_date = datetime.strptime(expire_str, '%Y-%m-%d').date() if expire_str else None
    sub, msg = create_subscription_for_admin(user_id, level, expire_date)
    if sub:
        return jsonify({'success': True, 'message': msg})
    else:
        return jsonify({'success': False, 'message': msg}), 400

@admin_bp.route('/users/<int:user_id>/status', methods=['POST'])
def set_user_status():
    data = request.get_json()
    status = data.get('status')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    user.status = status
    db.session.commit()
    return jsonify({'success': True, 'message': '用户状态已更新'})

@admin_bp.route('/devices', methods=['GET'])
def devices():
    devices = Device.query.filter_by(is_active=True).all()
    return jsonify({'success': True, 'devices': [{'id': d.id, 'user_id': d.user_id, 'device_name': d.device_name, 'last_login': d.last_login.isoformat()} for d in devices]})
