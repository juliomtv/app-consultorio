"""Sets g.tenant and g.tenant_settings before every request."""
from flask import g, session
from core.tenant_manager import resolve_tenant
from database.models import TenantSettings


def init_tenant_middleware(app):
    @app.before_request
    def load_tenant():
        from database.models import Tenant

        tenant = None

        # 1. Sessão do usuário logado — tem prioridade sobre URL em dev
        session_tenant_id = session.get('tenant_id')
        if session_tenant_id:
            tenant = Tenant.query.filter_by(id=session_tenant_id, is_active=True).first()

        # 2. URL-based resolution (subdomínio, custom domain, header)
        if not tenant:
            tenant = resolve_tenant()

        g.tenant    = tenant
        g.tenant_id = tenant.id if tenant else None

        if tenant:
            settings = TenantSettings.query.filter_by(tenant_id=tenant.id).first()
            if not settings:
                from database import db
                settings = TenantSettings(tenant_id=tenant.id)
                db.session.add(settings)
                db.session.commit()
            g.tenant_settings = settings
        else:
            g.tenant_settings = None
