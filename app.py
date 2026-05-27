import os
from flask import Flask, render_template, redirect, url_for
from config import get_config
from database import db, init_extensions


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'],    exist_ok=True)
    os.makedirs(app.config['DOCUMENTS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LIBRARY_FOLDER'],   exist_ok=True)
    os.makedirs(app.config['DATA_DIR'],          exist_ok=True)

    # Tenant middleware must run before Flask-Login so g.db is ready for user_loader
    from middleware.tenant import init_tenant_middleware
    init_tenant_middleware(app)

    init_extensions(app)

    # ── Blueprints ──────────────────────────────────────────────
    from routes.auth     import auth_bp
    from routes.admin    import admin_bp
    from routes.api      import api_bp
    from routes.internal import internal_bp

    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(api_bp,       url_prefix='/api/v1')
    app.register_blueprint(internal_bp,  url_prefix='/api/v1/internal')

    # ── Context processor (white-label) ─────────────────────────
    from core.context_processor import inject_tenant_settings
    app.context_processor(inject_tenant_settings)

    # ── Serve uploads ────────────────────────────────────────────
    from flask import send_from_directory

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # ── Root route ──────────────────────────────────────────────
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # ── Error handlers ──────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/404.html'), 403

    with app.app_context():
        _seed_defaults(app)

    return app


def _seed_defaults(app):
    """Seeds the default tenant DB on first run."""
    from database.tenant_db import open_session, db_exists
    from database.models import User, Tenant, TenantSettings

    slug = app.config.get('DEFAULT_TENANT_SLUG', 'demo')
    if db_exists(slug):
        return

    sess = open_session(slug)
    try:
        tenant = Tenant(
            name=app.config.get('DEFAULT_TENANT_NAME', 'Demo Clínica'),
            slug=slug,
            plan='enterprise',
            active_modules='clinica',
            is_active=True,
        )
        sess.add(tenant)
        sess.flush()

        settings = TenantSettings(
            tenant_id=tenant.id,
            company_name=app.config.get('DEFAULT_TENANT_NAME', 'Demo Clínica'),
        )
        sess.add(settings)

        admin_email = app.config.get('ADMIN_EMAIL', 'admin@consultorio.com')
        admin = User(
            name='Administrador',
            email=admin_email,
            role='admin',
            is_active=True,
            tenant_id=tenant.id,
        )
        admin.set_password(app.config.get('ADMIN_PASSWORD', 'Admin@2024!'))
        sess.add(admin)

        sess.commit()
        print(f'[SEED] Tenant padrão criado: {slug}')
    except Exception as e:
        sess.rollback()
        print(f'[SEED] Erro ao criar tenant padrão: {e}')
    finally:
        sess.close()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
