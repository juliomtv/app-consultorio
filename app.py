import os
from flask import Flask, render_template, redirect, url_for
from config import get_config
from database import db, init_extensions


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["DOCUMENTS_FOLDER"], exist_ok=True)
    os.makedirs(app.config["LIBRARY_FOLDER"], exist_ok=True)

    init_extensions(app)

    from routes.auth import auth_bp
    from routes.patient import patient_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(patient_bp, url_prefix="/paciente")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/404.html"), 403

    with app.app_context():
        db.create_all()
        _migrate_columns(app)
        _seed_admin(app)

    return app


def _migrate_columns(app):
    """Adiciona colunas novas em tabelas existentes (SQLite não suporta ALTER via ORM)."""
    from sqlalchemy import text
    new_cols = [
        ("appointments", "payment_type", "VARCHAR(20) DEFAULT 'particular'"),
        ("appointments", "plan_id",      "INTEGER REFERENCES health_plans(id)"),
    ]
    with db.engine.connect() as conn:
        for table, col, definition in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {definition}"))
                conn.commit()
            except Exception:
                pass  # coluna já existe


def _seed_admin(app):
    """Cria o admin padrão se não existir."""
    from database.models import User
    admin_email = app.config["ADMIN_EMAIL"]
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            name="Administrador",
            email=admin_email,
            role="admin",
            is_active=True,
        )
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        print(f"[SEED] Admin criado: {admin_email}")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
