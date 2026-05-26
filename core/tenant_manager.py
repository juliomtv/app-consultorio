"""
Tenant resolution — determines which tenant owns this request.

Resolution order:
1. Custom domain  (e.g. clinicaexemplo.com.br)
2. Subdomain      (e.g. slug.mysaas.com or slug.localhost)
3. X-Tenant-Slug  header (API clients / Postman / ngrok sem subdomínio)
4. Fallback       first active tenant (dev / demo — localhost sem slug)
"""
from flask import request, current_app
from database.models import Tenant

BARE_HOSTS = {'127.0.0.1', 'localhost'}  # sem subdomínio → vai pro fallback
MASTER_PREFIX = '/api/v1/internal'       # rotas internas não precisam de tenant


def resolve_tenant():
    """Return the Tenant for this request, or None if não identificado."""
    host = request.host.split(':')[0].lower()

    # Rotas internas do app-saas não precisam de contexto de tenant
    if request.path.startswith(MASTER_PREFIX):
        return None

    # 1. Domínio customizado exato (ex: clinica.com.br)
    if host not in BARE_HOSTS:
        tenant = Tenant.query.filter_by(custom_domain=host, is_active=True).first()
        if tenant:
            return tenant

    # 2. Subdomínio (slug.localhost ou slug.seudominio.com)
    parts = host.split('.')
    if len(parts) >= 2 and parts[0] not in ('www', 'api', 'app', '127', 'localhost'):
        tenant = Tenant.query.filter_by(slug=parts[0], is_active=True).first()
        if tenant:
            return tenant

    # 3. Header X-Tenant-Slug (ngrok sem subdomínio, Postman, apps mobile)
    slug_header = request.headers.get('X-Tenant-Slug')
    if slug_header:
        tenant = Tenant.query.filter_by(slug=slug_header, is_active=True).first()
        if tenant:
            return tenant

    # 4. Localhost sem subdomínio → sem tenant (mostra branding da plataforma)
    # O tenant correto será resolvido via sessão após o login.
    if host in BARE_HOSTS:
        return None

    # 5. Fallback de produção — usa o tenant padrão configurado no .env
    default_slug = current_app.config.get('DEFAULT_TENANT_SLUG', 'demo')
    tenant = Tenant.query.filter_by(slug=default_slug, is_active=True).first()
    if tenant:
        return tenant

    return Tenant.query.filter_by(is_active=True).first()
