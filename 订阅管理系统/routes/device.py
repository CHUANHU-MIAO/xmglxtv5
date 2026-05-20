from flask import Blueprint, request, jsonify, g
from services.auth_service import verify_token, get_user_devices, unbind_device, bind_device
from routes.subscription import auth_required

device_bp = Blueprint('device', __name__)

@device_bp.route('/list', methods=['GET'])
@auth_required
def list_devices():
    user = g.user
    devices = get_user_devices(user)
    current_device_id = request.args.get('current_device_id', '')
    return jsonify({
        'success': True,
        'devices': [
            {
                'id': d.id,
                'device_name': d.device_name,
                'device_id': d.device_id,
                'last_login': d.last_login.isoformat(),
                'is_current': d.device_id == current_device_id
            } for d in devices
        ],
        'max_devices': 2
    })

@device_bp.route('/unbind', methods=['POST'])
@auth_required
def unbind():
    user = g.user
    data = request.get_json()
    device_id = data.get('device_id')
    if not device_id:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    ok, msg = unbind_device(user, device_id)
    if ok:
        return jsonify({'success': True, 'message': msg})
    else:
        return jsonify({'success': False, 'message': msg}), 400

@device_bp.route('/bind', methods=['POST'])
@auth_required
def bind():
    user = g.user
    data = request.get_json()
    device_id = data.get('device_id')
    device_name = data.get('device_name') or '新设备'
    if not device_id:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    device, ok, msg = bind_device(user, device_id, device_name)
    if ok:
        return jsonify({'success': True, 'message': msg, 'device': {'id': device.id}})
    else:
        return jsonify({'success': False, 'message': msg, 'need_unbind': True, 'devices': [{'id': d.id, 'device_id': d.device_id, 'device_name': d.device_name} for d in get_user_devices(user)]}), 400
