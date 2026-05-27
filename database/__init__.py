from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()


def init_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    from database.models import User

    @login_manager.user_loader
    def load_user(user_id):
        from flask import g
        sess = getattr(g, 'db', None)
        if sess is None:
            return None
        return sess.query(User).get(int(user_id))
