"""Opens a per-tenant SQLite session (g.db) before every request."""
import re
from flask import g, session as flask_session, request, current_app


def init_tenant_middleware(app):
    @app.before_request
    def load_tenant():
        from database.tenant_db import open_session, db_exists
        from database.models import Tenant, TenantSettings

        slug = _resolve_slug()
        if not slug:
            slug = current_app.config.get('DEFAULT_TENANT_SLUG', 'demo')

        if not db_exists(slug):
            g.db             = None
            g.tenant         = None
            g.tenant_id      = None
            g.tenant_slug    = None
            g.tenant_settings = None
            return

        sess = open_session(slug)
        g.db          = sess
        g.tenant_slug = slug

        tenant = sess.query(Tenant).filter_by(is_active=True).first()
        g.tenant    = tenant
        g.tenant_id = tenant.id if tenant else None

        if tenant:
            settings = sess.query(TenantSettings).filter_by(tenant_id=tenant.id).first()
            if not settings:
                settings = TenantSettings(tenant_id=tenant.id)
                sess.add(settings)
                sess.commit()
            g.tenant_settings = settings
        else:
            g.tenant_settings = None

    @app.teardown_request
    def close_tenant_db(exc):
        sess = getattr(g, 'db', None)
        if sess is not None:
            if exc is not None:
                sess.rollback()
            sess.close()


def _resolve_slug() -> str:
    # 1. Header (API clients and SaaS-to-app calls)
    slug = request.headers.get('X-Tenant-Slug', '').strip()
    if slug:
        return slug

    # 2. Subdomain (e.g. minha-clinica.jvtechnologies.com.br)
    saas_domain = current_app.config.get('SAAS_DOMAIN', 'localhost')
    host = request.host.split(':')[0]
    if saas_domain and saas_domain != 'localhost' and host.endswith('.' + saas_domain):
        subdomain = host[: -len('.' + saas_domain)]
        if subdomain and re.match(r'^[a-z0-9][a-z0-9\-]+[a-z0-9]$', subdomain):
            return subdomain

    # 3. Session (stored at login for localhost/dev)
    slug = flask_session.get('tenant_slug', '').strip()
    if slug:
        return slug

    return ''
