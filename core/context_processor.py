"""Injects tenant branding into every template context."""
from flask import g


def inject_tenant_settings():
    tenant   = getattr(g, 'tenant', None)
    settings = getattr(g, 'tenant_settings', None)

    branding = {
        'company_name':  getattr(settings, 'company_name',  None) or 'JV Technologies',
        'tagline':       getattr(settings, 'tagline',        None) or 'Plataforma de gestão em saúde',
        'logo_url':      getattr(settings, 'logo_url',       None),
        'favicon_url':   getattr(settings, 'favicon_url',    None),
        'primary':       getattr(settings, 'primary_color',  None) or '#4F46E5',
        'secondary':     getattr(settings, 'secondary_color',None) or '#06B6D4',
        'bg_dark':       getattr(settings, 'bg_dark',        None) or '#0F172A',
        'whatsapp':      getattr(settings, 'whatsapp',       None) or '',
        'support_email': getattr(settings, 'support_email',  None) or '',
        'footer_text':   getattr(settings, 'footer_text',    None) or '',
        'custom_css':    getattr(settings, 'custom_css',     None) or '',
    }

    return dict(tenant=tenant, tenant_settings=settings, branding=branding)
