import random
import socket
import string
from datetime import datetime, timedelta

import jwt
from flask import Blueprint, request, jsonify, current_app
from models import db, User, PairSession, PhoneSession
from services.auth_service import hash_password, verify_password

pair_bp = Blueprint('pair', __name__)


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_phone_token(user_id):
    payload = {
        'user_id': user_id,
        'type': 'phone',
        'exp': datetime.utcnow() + timedelta(days=365)
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def verify_phone_token(token):
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        if payload.get('type') != 'phone':
            return None
        user = User.query.get(payload['user_id'])
        if not user or user.status != 'active':
            return None
        return user
    except Exception:
        return None

@pair_bp.route('/create', methods=['POST'])
def create_pair():
    data = request.get_json() or {}
    device_fingerprint = data.get('device_fingerprint', '')

    # 清理过期配对
    expire_time = datetime.utcnow() - timedelta(minutes=5)
    PairSession.query.filter(PairSession.created_at < expire_time, PairSession.status == 'pending').delete()
    db.session.commit()

    # 生成唯一配对码
    for _ in range(10):
        code = generate_code()
        if not PairSession.query.filter_by(code=code).first():
            break
    else:
        return jsonify({'success': False, 'message': '生成配对码失败'}), 500

    session = PairSession(
        code=code,
        status='pending',
        device_fingerprint=device_fingerprint,
        created_at=datetime.utcnow()
    )
    db.session.add(session)
    db.session.commit()

    # 优先使用配置的公网地址，否则用局域网 IP 替换 127.0.0.1
    public_url = current_app.config.get('SERVER_PUBLIC_URL', '')
    if public_url:
        qr_url = f'{public_url.rstrip("/")}/scan?code={code}'
    else:
        server_url = request.host_url.rstrip('/')
        if '127.0.0.1' in server_url:
            local_ip = get_local_ip()
            server_url = server_url.replace('127.0.0.1', local_ip)
        qr_url = f'{server_url}/scan?code={code}'

    return jsonify({
        'success': True,
        'code': code,
        'qr_url': qr_url,
        'expires_in': 300
    })

@pair_bp.route('/status', methods=['GET'])
def pair_status():
    code = request.args.get('code', '')
    session = PairSession.query.filter_by(code=code).first()
    if not session:
        return jsonify({'success': False, 'message': '配对码无效'}), 404

    # 检查是否过期
    if session.status == 'pending' and datetime.utcnow() - session.created_at > timedelta(minutes=5):
        session.status = 'expired'
        db.session.commit()

    result = {
        'success': True,
        'status': session.status,
    }

    if session.status == 'confirmed' and session.user_id:
        user = User.query.get(session.user_id)
        if user:
            from services.auth_service import create_token, bind_device
            token = create_token(user.id)
            sub = get_user_subscription(user)
            result['token'] = token
            result['user'] = {
                'id': user.id,
                'username': user.username,
                'subscription': {
                    'level': sub.level,
                    'max_projects': sub.max_projects,
                    'expire_date': sub.expire_date.isoformat() if sub.expire_date else None
                }
            }
            # 绑定设备
            if session.device_fingerprint:
                bind_device(user, session.device_fingerprint, 'desktop')

    return jsonify(result)

@pair_bp.route('/confirm', methods=['POST'])
def pair_confirm():
    data = request.get_json() or {}
    code = data.get('code', '')
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    phone_token = data.get('phone_token', '')

    session = PairSession.query.filter_by(code=code).first()
    if not session:
        return jsonify({'success': False, 'message': '配对码无效'}), 404
    if session.status != 'pending':
        return jsonify({'success': False, 'message': '配对码已处理'}), 400
    if datetime.utcnow() - session.created_at > timedelta(minutes=5):
        session.status = 'expired'
        db.session.commit()
        return jsonify({'success': False, 'message': '配对码已过期，请重新生成'}), 400

    user = None
    # 优先用 phone_token 自动确认
    if phone_token:
        user = verify_phone_token(phone_token)

    # 用用户名密码登录或注册
    if not user and username and password:
        user = User.query.filter_by(username=username).first()
        if user:
            if not verify_password(password, user.password_hash):
                return jsonify({'success': False, 'message': '密码错误'}), 401
            if user.status != 'active':
                return jsonify({'success': False, 'message': '账户已被禁用'}), 403
        else:
            user = User(
                username=username,
                password_hash=hash_password(password),
                status='active'
            )
            db.session.add(user)
            db.session.commit()

    if not user:
        return jsonify({'success': False, 'message': '请提供有效的登录信息'}), 400

    # 关联用户到配对会话
    session.user_id = user.id
    session.status = 'confirmed'
    session.confirmed_at = datetime.utcnow()
    db.session.commit()

    # 生成/更新 phone_token
    pt = generate_phone_token(user.id)
    existing_phone = PhoneSession.query.filter_by(user_id=user.id).first()
    if existing_phone:
        existing_phone.phone_token = pt
        existing_phone.last_used_at = datetime.utcnow()
    else:
        phone_sess = PhoneSession(
            user_id=user.id,
            phone_token=pt,
            user_agent=request.headers.get('User-Agent', '')[:255],
        )
        db.session.add(phone_sess)
    db.session.commit()

    return jsonify({
        'success': True,
        'phone_token': pt,
        'username': user.username
    })


def get_user_subscription(user):
    from services.subscription_service import get_user_subscription as gus
    return gus(user)