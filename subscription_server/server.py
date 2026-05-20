import os
from flask import Flask, jsonify
from config import Config
from models import db
from routes.auth import auth_bp
from routes.subscription import sub_bp
from routes.device import device_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(sub_bp, url_prefix='/api/subscription')
app.register_blueprint(device_bp, url_prefix='/api/device')
app.register_blueprint(admin_bp, url_prefix='/admin/api')

@app.route('/')
def index():
    return jsonify({'service': 'Subscription Server', 'status': 'running'})

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'message': '接口不存在'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'message': '服务器内部错误'}), 500

def init_db():
    with app.app_context():
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)
