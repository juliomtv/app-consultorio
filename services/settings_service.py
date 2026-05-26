"""CRUD helpers for TenantSettings."""
from database import db
from database.models import TenantSettings

_ALLOWED = {
    'company_name', 'tagline', 'logo_url', 'favicon_url',
    'primary_color', 'secondary_color', 'bg_dark',
    'whatsapp', 'support_email', 'address', 'footer_text', 'custom_css',
}


def get_settings(tenant_id: int) -> TenantSettings:
    s = TenantSettings.query.filter_by(tenant_id=tenant_id).first()
    if not s:
        s = TenantSettings(tenant_id=tenant_id)
        db.session.add(s)
        db.session.commit()
    return s


def update_settings(tenant_id: int, data: dict) -> TenantSettings:
    s = get_settings(tenant_id)
    for key, val in data.items():
        if key in _ALLOWED:
            setattr(s, key, val or None)
    db.session.commit()
    return s
