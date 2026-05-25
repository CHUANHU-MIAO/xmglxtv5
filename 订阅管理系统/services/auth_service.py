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

def check_unique(username=None, email=None, phone=None):
    if username and User.query.filter_by(username=username).first():
        return 'username'
    if email and User.query.filter_by(email=email).first():
        return 'email'
    if phone and User.query.filter_by(phone=phone).first():
        return 'phone'
    return None

def create_user(username, password, email=None, phone=None):
    dup = check_unique(username=username, email=email, phone=phone)
    if dup == 'username':
        return None, '用户名已存在'
    if dup == 'email':
        return None, '该邮箱已被注册'
    if dup == 'phone':
        return None, '该手机号已被注册'
    hashed = hash_password(password)
    user = User(username=username, password_hash=hashed, email=email, phone=phone)
    db.session.add(user)
    db.session.commit()
    from services.subscription_service import SUBSCRIPTION_LEVELS
    sub = Subscription(
        user_id=user.id,
        level='standard',
        max_projects=SUBSCRIPTION_LEVELS['standard']['max_projects'],
        status='active'
    )
    db.session.add(sub)
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


def forgot_password_verify(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return None, '用户不存在'
    masked_email = None
    if user.email and '@' in user.email:
        name, domain = user.email.split('@')
        masked_email = name[0] + '****' + name[-1] + '@' + domain if len(name) > 2 else name[0] + '****@' + domain
    masked_phone = None
    if user.phone and len(user.phone) >= 7:
        masked_phone = user.phone[:3] + '****' + user.phone[-4:]
    has_old_pwd = bool(user.old_password_hash)
    return {
        'user_id': user.id,
        'username': user.username,
        'masked_email': masked_email,
        'masked_phone': masked_phone,
        'has_old_password': has_old_pwd,
    }, None


def verify_and_reset_password(username, verify_methods, new_password):
    user = User.query.filter_by(username=username).first()
    if not user:
        return False, '用户不存在'
    if len(verify_methods) < 2:
        return False, '请至少选择两种验证方式'
    passed = 0
    for vm in verify_methods:
        method = vm.get('method')
        value = vm.get('value', '')
        if method == 'email':
            if user.email and value == 'verified':
                passed += 1
        elif method == 'phone':
            if user.phone and value == 'verified':
                passed += 1
        elif method == 'old_password':
            if user.old_password_hash and verify_password(value, user.old_password_hash):
                passed += 1
    if passed < 2:
        return False, '身份验证未通过，请确认信息是否正确'
    user.old_password_hash = user.password_hash
    user.password_hash = hash_password(new_password)
    db.session.commit()
    return True, '密码重置成功'


def update_password(user_id, old_password, new_password):
    user = User.query.get(user_id)
    if not user:
        return False, '用户不存在'
    if not verify_password(old_password, user.password_hash):
        return False, '原密码错误'
    user.old_password_hash = user.password_hash
    user.password_hash = hash_password(new_password)
    db.session.commit()
    return True, '密码修改成功'
