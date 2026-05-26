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

    # ── Tenant middleware ────────────────────────────────────────
    from middleware.tenant import init_tenant_middleware
    init_tenant_middleware(app)

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
        db.create_all()
        _migrate_columns(app)
        _seed_defaults(app)

    return app


def _migrate_columns(app):
    """Adds new columns to existing tables (SQLite ALTER workaround)."""
    from sqlalchemy import text
    new_cols = [
        ('appointments', 'payment_type',   "VARCHAR(20) DEFAULT 'particular'"),
        ('appointments', 'plan_id',        'INTEGER REFERENCES health_plans(id)'),
        ('users',        'tenant_id',      'INTEGER'),
        ('users',        'is_demo',        'BOOLEAN NOT NULL DEFAULT 0'),
        ('tenants',      'demo_expires_at','DATETIME'),
    ]
    with db.engine.connect() as conn:
        for table, col, definition in new_cols:
            try:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {definition}'))
                conn.commit()
            except Exception:
                pass  # column already exists


def _seed_defaults(app):
    """Seeds the default tenant and admin on first run."""
    from database.models import User, Tenant, TenantSettings

    # 1. Default tenant
    tenant = Tenant.query.filter_by(slug=app.config['DEFAULT_TENANT_SLUG']).first()
    if not tenant:
        tenant = Tenant(
            name=app.config['DEFAULT_TENANT_NAME'],
            slug=app.config['DEFAULT_TENANT_SLUG'],
            plan='enterprise',
            active_modules='clinica',
            is_active=True,
        )
        db.session.add(tenant)
        db.session.flush()

        settings = TenantSettings(
            tenant_id=tenant.id,
            company_name=app.config['DEFAULT_TENANT_NAME'],
        )
        db.session.add(settings)
        db.session.commit()
        print(f'[SEED] Tenant criado: {tenant.slug}')

    # 2. Assign orphan users to default tenant
    from sqlalchemy import text
    with db.engine.connect() as conn:
        conn.execute(text(
            f"UPDATE users SET tenant_id = {tenant.id} WHERE tenant_id IS NULL"
        ))
        conn.commit()

    # 3. Tenant admin
    admin_email = app.config['ADMIN_EMAIL']
    if not User.query.filter_by(email=admin_email).first():
        try:
            admin = User(
                name='Administrador',
                email=admin_email,
                role='admin',
                is_active=True,
                tenant_id=tenant.id,
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
            db.session.commit()
            print(f'[SEED] Admin criado: {admin_email}')
        except Exception:
            db.session.rollback()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
