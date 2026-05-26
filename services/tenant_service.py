"""Tenant lifecycle management."""
from datetime import datetime, timedelta
from database import db
from database.models import Tenant, TenantSettings, User
from core.db_manager import DBManager


def create_tenant(
    name: str,
    slug: str,
    plan: str = 'basic',
    admin_email: str = None,
    admin_password: str = None,
    db_url: str = None,
    custom_domain: str = None,
    trial_days: int = 30,
) -> Tenant:
    tenant = Tenant(
        name=name,
        slug=slug.lower().strip(),
        plan=plan,
        db_url=db_url or None,
        custom_domain=custom_domain or None,
        active_modules='clinica',
        is_active=True,
        trial_ends_at=datetime.utcnow() + timedelta(days=trial_days),
    )
    db.session.add(tenant)
    db.session.flush()

    settings = TenantSettings(tenant_id=tenant.id, company_name=name)
    db.session.add(settings)

    if admin_email and admin_password:
        admin = User(
            name='Administrador',
            email=admin_email,
            role='admin',
            is_active=True,
            tenant_id=tenant.id,
        )
        admin.set_password(admin_password)
        db.session.add(admin)

    db.session.commit()
    return tenant


def deactivate_tenant(tenant_id: int):
    Tenant.query.filter_by(id=tenant_id).update({'is_active': False})
    db.session.commit()
    DBManager.invalidate(tenant_id)


def get_tenant_stats(tenant_id: int) -> dict:
    from database.models import Appointment
    patients = User.query.filter_by(role='patient', tenant_id=tenant_id).count()
    appts    = Appointment.query.join(
        User, Appointment.patient_id == User.id
    ).filter(User.tenant_id == tenant_id).count()
    return {'patients': patients, 'appointments': appts}
