from flask import Blueprint, request, jsonify, g
from services.auth_service import verify_token
from services.subscription_service import get_user_subscription, check_subscription_valid

sub_bp = Blueprint('subscription', __name__)

def auth_required(f):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': '未登录'}), 401
        token = auth_header.split(' ')[1]
        user = verify_token(token)
        if not user:
            return jsonify({'success': False, 'message': '登录已过期'}), 401
        g.user = user
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@sub_bp.route('/info', methods=['GET'])
@auth_required
def info():
    user = g.user
    sub = get_user_subscription(user)
    valid = check_subscription_valid(sub)
    return jsonify({
        'success': True,
        'subscription': {
            'level': sub.level,
            'max_projects': sub.max_projects,
            'current_projects': 0,
            'start_date': sub.start_date.isoformat(),
            'expire_date': sub.expire_date.isoformat() if sub.expire_date else None,
            'status': sub.status if valid else 'expired'
        }
    })
