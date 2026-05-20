from flask import Flask
from web.config import Config
from web.extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from web.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from web.blueprints.auth import auth_bp
    from web.blueprints.projects import projects_bp
    from web.blueprints.admin import admin_bp
    from web.blueprints.files import files_bp
    from web.blueprints.estimation import estimation_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(estimation_bp)

    with app.app_context():
        db.create_all()

    return app
