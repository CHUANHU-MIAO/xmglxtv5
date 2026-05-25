from datetime import datetime, timedelta
from models import db, User, Subscription

SUBSCRIPTION_LEVELS = {
    'standard': {'max_projects': 10, 'has_formula': False},
    'pro': {'max_projects': 50, 'has_formula': True},
    'max': {'max_projects': 999999, 'has_formula': True}
}

def get_user_subscription(user):
    sub = Subscription.query.filter_by(user_id=user.id, status='active').order_by(Subscription.id.desc()).first()
    if not sub:
        sub = Subscription(
            user_id=user.id,
            level='standard',
            max_projects=10,
            status='active'
        )
        db.session.add(sub)
        db.session.commit()
    return sub

def check_subscription_valid(sub):
    if not sub or sub.status != 'active':
        return False
    if sub.expire_date and sub.expire_date < datetime.utcnow().date():
        return False
    return True

def upgrade_subscription(user, new_level, duration_months=12):
    level_config = SUBSCRIPTION_LEVELS.get(new_level)
    if not level_config:
        return None, '无效的订阅等级'
    existing = get_user_subscription(user)
    if existing:
        existing.status = 'cancelled'
    start_date = datetime.utcnow().date()
    expire_date = start_date + timedelta(days=30 * duration_months)
    sub = Subscription(
        user_id=user.id,
        level=new_level,
        max_projects=level_config['max_projects'],
        start_date=start_date,
        expire_date=expire_date,
        status='active'
    )
    db.session.add(sub)
    db.session.commit()
    return sub, '订阅升级成功'

def create_subscription_for_admin(user_id, level, expire_date):
    level_config = SUBSCRIPTION_LEVELS.get(level)
    if not level_config:
        return None, '无效的订阅等级'
    old = Subscription.query.filter_by(user_id=user_id, status='active').first()
    if old:
        old.status = 'cancelled'
    sub = Subscription(
        user_id=user_id,
        level=level,
        max_projects=level_config['max_projects'],
        start_date=datetime.utcnow().date(),
        expire_date=expire_date,
        status='active'
    )
    db.session.add(sub)
    db.session.commit()
    return sub, '订阅创建成功'
