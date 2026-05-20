import bcrypt
import jwt
from datetime import datetime, timedelta
from flask import current_app
from models import db, User, Subscription, Device

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def create_user(username, password, email=None):
    if User.query.filter_by(username=username).first():
        return None, '用户名已存在'
    hashed = hash_password(password)
    user = User(username=username, password_hash=hashed, email=email)
    db.session.add(user)
    db.session.commit()
    return user, '注册成功'

def login_user(username, password):
    user = User.query.filter_by(username=username, status='active').first()
    if not user or not verify_password(password, user.password_hash):
        return None, '用户名或密码错误'
    user.last_login = datetime.utcnow()
    db.session.commit()
    return user, '登录成功'

def create_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])
        if not user or user.status != 'active':
            return None
        return user
    except:
        return None

def bind_device(user, device_id, device_name):
    active_devices = Device.query.filter_by(user_id=user.id, is_active=True).count()
    existing = Device.query.filter_by(user_id=user.id, device_id=device_id, is_active=True).first()
    if existing:
        existing.last_login = datetime.utcnow()
        db.session.commit()
        return existing, True, '设备已绑定'
    if active_devices >= 2:
        return None, False, '已达设备上限，请先解绑其他设备'
    device = Device(user_id=user.id, device_id=device_id, device_name=device_name)
    db.session.add(device)
    db.session.commit()
    return device, True, '设备绑定成功'

def unbind_device(user, device_id):
    device = Device.query.filter_by(user_id=user.id, device_id=device_id, is_active=True).first()
    if not device:
        return False, '设备不存在'
    device.is_active = False
    db.session.commit()
    return True, '设备已解绑'

def get_user_devices(user):
    return Device.query.filter_by(user_id=user.id, is_active=True).all()
