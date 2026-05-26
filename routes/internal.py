"""
Rotas internas — chamadas pelo app-saas para provisionar tenants.
Autenticação: header X-Internal-Key deve coincidir com INTERNAL_API_KEY do config.
"""
from flask import Blueprint, jsonify, request, current_app
from database import db
from database.models import Tenant, TenantSettings, User

internal_bp = Blueprint('internal', __name__)

_SETTINGS_KEYS = (
    'company_name', 'tagline', 'logo_url', 'favicon_url',
    'primary_color', 'secondary_color', 'bg_dark',
    'whatsapp', 'support_email', 'address', 'footer_text', 'custom_css',
)


def _auth():
    key = request.headers.get('X-Internal-Key', '')
    return key and key == current_app.config.get('INTERNAL_API_KEY', '')


def _resp(data=None, error=None, status=200):
    payload = {'status': 'error' if error else 'ok'}
    if data:  payload['data']  = data
    if error: payload['error'] = error
    return jsonify(payload), status


@internal_bp.route('/provision', methods=['POST'])
def provision():
    """Cria ou atualiza um tenant + admin no app-consultorio. Idempotente."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    body           = request.get_json(silent=True) or {}
    slug           = body.get('slug', '').strip()
    name           = body.get('name', slug)
    plan           = body.get('plan', 'basic')
    admin_email    = body.get('admin_email', '').strip()
    admin_password = body.get('admin_password', '')
    custom_domain  = body.get('custom_domain') or None
    modules        = body.get('modules', 'clinica')
    settings_data  = body.get('settings', {})

    if not slug or not admin_email or not admin_password:
        return _resp(error='slug, admin_email e admin_password são obrigatórios', status=400)

    # Tenant — cria ou atualiza
    tenant = Tenant.query.filter_by(slug=slug).first()
    if not tenant:
        tenant = Tenant(slug=slug)
        db.session.add(tenant)
    tenant.name          = name
    tenant.plan          = plan
    tenant.custom_domain = custom_domain
    tenant.active_modules = modules
    tenant.is_active     = True
    db.session.flush()

    # TenantSettings
    s = TenantSettings.query.filter_by(tenant_id=tenant.id).first()
    if not s:
        s = TenantSettings(tenant_id=tenant.id)
        db.session.add(s)
    s.company_name = settings_data.get('company_name', name)
    for key in _SETTINGS_KEYS:
        if key in settings_data and key != 'company_name':
            setattr(s, key, settings_data[key] or None)

    # Admin user — busca pelo tenant primeiro, depois pelo e-mail
    admin = User.query.filter_by(email=admin_email, tenant_id=tenant.id).first()
    if not admin:
        # Se e-mail já existe em outro tenant, cria com e-mail único por tenant
        other = User.query.filter_by(email=admin_email).first()
        effective_email = f"{admin_email}+{tenant.slug}" if other else admin_email
        admin = User(
            name='Administrador',
            email=effective_email,
            role='admin',
            is_active=True,
            tenant_id=tenant.id,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
    else:
        admin.set_password(admin_password)
        admin.role      = 'admin'
        admin.is_active = True

    db.session.commit()
    return _resp({'tenant_id': tenant.id, 'slug': tenant.slug})


@internal_bp.route('/tenant/<slug>/settings', methods=['PUT'])
def update_settings(slug):
    """Sincroniza configurações de white-label enviadas pelo app-saas."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    tenant = Tenant.query.filter_by(slug=slug).first()
    if not tenant:
        return _resp(error='Tenant não encontrado', status=404)

    body = request.get_json(silent=True) or {}
    s = TenantSettings.query.filter_by(tenant_id=tenant.id).first()
    if not s:
        s = TenantSettings(tenant_id=tenant.id)
        db.session.add(s)
    for key in _SETTINGS_KEYS:
        if key in body:
            setattr(s, key, body[key] or None)
    db.session.commit()
    return _resp()


@internal_bp.route('/tenant/<slug>/status', methods=['PUT'])
def set_status(slug):
    """Ativa ou desativa um tenant."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    tenant = Tenant.query.filter_by(slug=slug).first()
    if not tenant:
        return _resp(error='Tenant não encontrado', status=404)

    body = request.get_json(silent=True) or {}
    tenant.is_active = bool(body.get('is_active', True))
    db.session.commit()
    return _resp()


@internal_bp.route('/tenant/<slug>/demo', methods=['POST'])
def set_demo(slug):
    """Cria/atualiza usuário demo e define expiração no tenant."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    tenant = Tenant.query.filter_by(slug=slug).first()
    if not tenant:
        return _resp(error='Tenant não encontrado', status=404)

    body          = request.get_json(silent=True) or {}
    demo_email    = body.get('demo_email', '').strip()
    demo_password = body.get('demo_password', '')
    expires_raw   = body.get('demo_expires_at')

    if expires_raw:
        from datetime import datetime as _dt
        try:
            tenant.demo_expires_at = _dt.fromisoformat(expires_raw.replace('Z', '+00:00').replace('+00:00', ''))
        except Exception:
            pass

    demo_user = User.query.filter_by(email=demo_email, tenant_id=tenant.id).first()
    if not demo_user:
        demo_user = User(name='Demo', email=demo_email, role='admin',
                        is_active=True, is_demo=True, tenant_id=tenant.id)
        db.session.add(demo_user)
    else:
        demo_user.is_active = True
        demo_user.is_demo   = True
        demo_user.role      = 'admin'

    demo_user.set_password(demo_password)
    db.session.commit()
    return _resp()


@internal_bp.route('/tenant/<slug>/seed', methods=['POST'])
def seed_demo(slug):
    """Popula o tenant com dados de demonstração realistas."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    tenant = Tenant.query.filter_by(slug=slug).first()
    if not tenant:
        return _resp(error='Tenant não encontrado', status=404)

    try:
        _seed_tenant(tenant)
        return _resp({'message': 'Seeded successfully'})
    except Exception as e:
        current_app.logger.error(f'[SEED] {e}')
        return _resp(error=str(e), status=500)


def _seed_tenant(tenant):
    from datetime import date, timedelta
    from database.models import Professional, Appointment, HealthPlan, Schedule

    tid = tenant.id

    # ── Limpar dados do tenant (exceto admins) ────────────────────
    # Appointments first (FK constraints)
    patient_ids = [u.id for u in User.query.filter_by(tenant_id=tid, role='patient').all()]
    if patient_ids:
        Appointment.query.filter(Appointment.patient_id.in_(patient_ids)).delete(synchronize_session=False)
    prof_user_ids = [u.id for u in User.query.filter_by(tenant_id=tid, role='professional').all()]
    for pu_id in prof_user_ids:
        prof = Professional.query.filter_by(user_id=pu_id).first()
        if prof:
            Schedule.query.filter_by(professional_id=prof.id).delete()
            db.session.delete(prof)
    User.query.filter_by(tenant_id=tid, role='patient').delete()
    User.query.filter_by(tenant_id=tid, role='professional').delete()
    db.session.flush()

    # ── Planos de saúde ───────────────────────────────────────────
    plans = []
    for name, op, val in [
        ('Unimed Demo',    'Unimed',    180.0),
        ('Bradesco Saúde', 'Bradesco',  220.0),
    ]:
        hp = HealthPlan(name=name, operator=op, consultation_value=val, is_active=True)
        db.session.add(hp)
        plans.append(hp)
    db.session.flush()

    # ── Profissionais ─────────────────────────────────────────────
    prof_data = [
        ('Dra. Ana Beatriz Santos', 'ana.demo@clinica.br', 'Ginecologia e Obstetrícia', 'CRM 12345', 'CRM'),
        ('Dr. Carlos Eduardo Lima',  'carlos.demo@clinica.br', 'Clínica Geral',          'CRM 67890', 'CRM'),
    ]
    profs = []
    for name, email, spec, council_no, council_type in prof_data:
        u = User(name=name, email=email, role='professional',
                 is_active=True, tenant_id=tid)
        u.set_password('Demo@2026!')
        db.session.add(u)
        db.session.flush()
        p = Professional(user_id=u.id, specialty=spec,
                         council_number=council_no, council_type=council_type,
                         consultation_duration=30, is_active=True)
        db.session.add(p)
        db.session.flush()
        # Agenda seg-sex 08:00-18:00
        for day in range(5):
            db.session.add(Schedule(professional_id=p.id, day_of_week=day,
                                    start_time='08:00', end_time='18:00',
                                    slot_duration=30, is_active=True))
        profs.append(p)
    db.session.flush()

    # ── Pacientes ─────────────────────────────────────────────────
    PATIENTS = [
        ('Maria Silva',       'maria.demo@paciente.br',   '(21) 98765-0001'),
        ('Fernanda Costa',    'fernanda.demo@paciente.br', '(21) 98765-0002'),
        ('Juliana Oliveira',  'juliana.demo@paciente.br',  '(21) 98765-0003'),
        ('Camila Rodrigues',  'camila.demo@paciente.br',   '(21) 98765-0004'),
        ('Patricia Alves',    'patricia.demo@paciente.br', '(21) 98765-0005'),
        ('Renata Souza',      'renata.demo@paciente.br',   '(21) 98765-0006'),
        ('Beatriz Lima',      'beatriz.demo@paciente.br',  '(21) 98765-0007'),
        ('Amanda Santos',     'amanda.demo@paciente.br',   '(21) 98765-0008'),
    ]
    patients = []
    for name, email, phone in PATIENTS:
        u = User(name=name, email=email, phone=phone, role='patient',
                 is_active=True, tenant_id=tid)
        u.set_password('Demo@2026!')
        db.session.add(u)
        patients.append(u)
    db.session.flush()

    # ── Consultas ─────────────────────────────────────────────────
    today = date.today()
    times = ['08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '14:00', '14:30', '15:00']
    APPT_TYPES = ['Consulta', 'Retorno', 'Consulta', 'Consulta', 'Retorno']

    slot = 0
    for delta in range(-14, 15):
        d = today + timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        if delta < 0:
            status = 'completed' if delta % 5 != 0 else 'cancelled'
        elif delta == 0:
            status = 'confirmed'
        else:
            status = 'scheduled'
        for _ in range(2):
            patient  = patients[slot % len(patients)]
            prof     = profs[slot % len(profs)]
            appt_type = APPT_TYPES[slot % len(APPT_TYPES)]
            t        = times[slot % len(times)]
            pay_type = 'convenio' if slot % 3 == 0 else 'particular'
            plan_id  = plans[0].id if pay_type == 'convenio' else None
            price    = (plans[0].consultation_value if pay_type == 'convenio' else 200.0)
            db.session.add(Appointment(
                patient_id=patient.id, professional_id=prof.id,
                date=d, time=t, duration=30,
                status=status, type=appt_type,
                payment_type=pay_type, plan_id=plan_id,
                price=price, is_paid=(delta < 0),
            ))
            slot += 1
    db.session.commit()


@internal_bp.route('/tenant/<slug>', methods=['DELETE'])
def deprovision(slug):
    """Remove tenant e todos os seus dados do app-consultorio."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    tenant = Tenant.query.filter_by(slug=slug).first()
    if tenant:
        db.session.delete(tenant)
        db.session.commit()
    return _resp()  # 200 mesmo se não existia (idempotente)
