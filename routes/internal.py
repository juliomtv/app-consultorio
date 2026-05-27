"""
Rotas internas — chamadas pelo app-saas para provisionar tenants.
Autenticação: header X-Internal-Key deve coincidir com INTERNAL_API_KEY do config.
"""
from flask import Blueprint, jsonify, request, current_app
from database.tenant_db import open_session
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

    sess = open_session(slug)
    try:
        # Tenant
        tenant = sess.query(Tenant).first()
        if not tenant:
            tenant = Tenant(slug=slug)
            sess.add(tenant)
        tenant.name           = name
        tenant.plan           = plan
        tenant.custom_domain  = custom_domain
        tenant.active_modules = modules
        tenant.is_active      = True
        sess.flush()

        # TenantSettings
        s = sess.query(TenantSettings).filter_by(tenant_id=tenant.id).first()
        if not s:
            s = TenantSettings(tenant_id=tenant.id)
            sess.add(s)
        s.company_name = settings_data.get('company_name', name)
        for key in _SETTINGS_KEYS:
            if key in settings_data and key != 'company_name':
                setattr(s, key, settings_data[key] or None)

        # Admin user
        admin = sess.query(User).filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                name='Administrador',
                email=admin_email,
                role='admin',
                is_active=True,
                tenant_id=tenant.id,
            )
            admin.set_password(admin_password)
            sess.add(admin)
        else:
            admin.set_password(admin_password)
            admin.role      = 'admin'
            admin.is_active = True

        sess.commit()
        return _resp({'tenant_id': tenant.id, 'slug': tenant.slug})
    except Exception as e:
        sess.rollback()
        current_app.logger.error(f'[PROVISION] {e}')
        return _resp(error=str(e), status=500)
    finally:
        sess.close()


@internal_bp.route('/tenant/<slug>/settings', methods=['PUT'])
def update_settings(slug):
    """Sincroniza configurações de white-label enviadas pelo app-saas."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    sess = open_session(slug)
    try:
        tenant = sess.query(Tenant).first()
        if not tenant:
            return _resp(error='Tenant não encontrado', status=404)

        body = request.get_json(silent=True) or {}
        s = sess.query(TenantSettings).filter_by(tenant_id=tenant.id).first()
        if not s:
            s = TenantSettings(tenant_id=tenant.id)
            sess.add(s)
        for key in _SETTINGS_KEYS:
            if key in body:
                setattr(s, key, body[key] or None)
        sess.commit()
        return _resp()
    except Exception as e:
        sess.rollback()
        return _resp(error=str(e), status=500)
    finally:
        sess.close()


@internal_bp.route('/tenant/<slug>/status', methods=['PUT'])
def set_status(slug):
    """Ativa ou desativa um tenant."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    sess = open_session(slug)
    try:
        tenant = sess.query(Tenant).first()
        if not tenant:
            return _resp(error='Tenant não encontrado', status=404)

        body = request.get_json(silent=True) or {}
        tenant.is_active = bool(body.get('is_active', True))
        sess.commit()
        return _resp()
    except Exception as e:
        sess.rollback()
        return _resp(error=str(e), status=500)
    finally:
        sess.close()


@internal_bp.route('/tenant/<slug>/demo', methods=['POST'])
def set_demo(slug):
    """Cria/atualiza usuário demo e define expiração no tenant."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    sess = open_session(slug)
    try:
        tenant = sess.query(Tenant).first()
        if not tenant:
            return _resp(error='Tenant não encontrado', status=404)

        body          = request.get_json(silent=True) or {}
        demo_email    = body.get('demo_email', '').strip()
        demo_password = body.get('demo_password', '')
        expires_raw   = body.get('demo_expires_at')

        if expires_raw:
            from datetime import datetime as _dt
            try:
                tenant.demo_expires_at = _dt.fromisoformat(
                    expires_raw.replace('Z', '+00:00').replace('+00:00', '')
                )
            except Exception:
                pass

        demo_user = sess.query(User).filter_by(email=demo_email).first()
        if not demo_user:
            demo_user = User(name='Demo', email=demo_email, role='admin',
                             is_active=True, is_demo=True, tenant_id=tenant.id)
            sess.add(demo_user)
        else:
            demo_user.is_active = True
            demo_user.is_demo   = True
            demo_user.role      = 'admin'

        demo_user.set_password(demo_password)
        sess.commit()
        return _resp()
    except Exception as e:
        sess.rollback()
        return _resp(error=str(e), status=500)
    finally:
        sess.close()


@internal_bp.route('/tenant/<slug>/seed', methods=['POST'])
def seed_demo(slug):
    """Popula o tenant com dados de demonstração realistas."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    sess = open_session(slug)
    try:
        tenant = sess.query(Tenant).first()
        if not tenant:
            return _resp(error='Tenant não encontrado', status=404)
        _seed_tenant(sess, tenant)
        return _resp({'message': 'Seeded successfully'})
    except Exception as e:
        sess.rollback()
        current_app.logger.error(f'[SEED] {e}')
        return _resp(error=str(e), status=500)
    finally:
        sess.close()


def _seed_tenant(sess, tenant):
    from datetime import date, timedelta
    from database.models import Professional, Appointment, HealthPlan, Schedule

    tid = tenant.id

    # ── Limpar dados existentes (exceto admins) ──────────────────────────────
    for appt in sess.query(Appointment).all():
        sess.delete(appt)
    for prof in sess.query(Professional).all():
        for sch in sess.query(Schedule).filter_by(professional_id=prof.id).all():
            sess.delete(sch)
        sess.delete(prof)
    for u in sess.query(User).filter(User.role.in_(['patient', 'professional'])).all():
        sess.delete(u)
    for hp in sess.query(HealthPlan).all():
        sess.delete(hp)
    sess.flush()

    # ── Planos de saúde ──────────────────────────────────────────────────────
    plans = []
    for name, op, val in [
        ('Unimed Demo',    'Unimed',   180.0),
        ('Bradesco Saúde', 'Bradesco', 220.0),
    ]:
        hp = HealthPlan(name=name, operator=op, consultation_value=val, is_active=True)
        sess.add(hp)
        plans.append(hp)
    sess.flush()

    # ── Profissionais ────────────────────────────────────────────────────────
    prof_data = [
        ('Dra. Ana Beatriz Santos', 'ana.demo@clinica.br',    'Ginecologia e Obstetrícia', 'CRM 12345', 'CRM'),
        ('Dr. Carlos Eduardo Lima',  'carlos.demo@clinica.br', 'Clínica Geral',             'CRM 67890', 'CRM'),
    ]
    profs = []
    for name, email, spec, council_no, council_type in prof_data:
        u = User(name=name, email=email, role='professional',
                 is_active=True, tenant_id=tid)
        u.set_password('Demo@2026!')
        sess.add(u)
        sess.flush()
        p = Professional(user_id=u.id, specialty=spec,
                         council_number=council_no, council_type=council_type,
                         consultation_duration=30, is_active=True)
        sess.add(p)
        sess.flush()
        for day in range(5):
            sess.add(Schedule(professional_id=p.id, day_of_week=day,
                              start_time='08:00', end_time='18:00',
                              slot_duration=30, is_active=True))
        profs.append(p)
    sess.flush()

    # ── Pacientes ────────────────────────────────────────────────────────────
    PATIENTS = [
        ('Maria Silva',      'maria.demo@paciente.br',    '(21) 98765-0001'),
        ('Fernanda Costa',   'fernanda.demo@paciente.br', '(21) 98765-0002'),
        ('Juliana Oliveira', 'juliana.demo@paciente.br',  '(21) 98765-0003'),
        ('Camila Rodrigues', 'camila.demo@paciente.br',   '(21) 98765-0004'),
        ('Patricia Alves',   'patricia.demo@paciente.br', '(21) 98765-0005'),
        ('Renata Souza',     'renata.demo@paciente.br',   '(21) 98765-0006'),
        ('Beatriz Lima',     'beatriz.demo@paciente.br',  '(21) 98765-0007'),
        ('Amanda Santos',    'amanda.demo@paciente.br',   '(21) 98765-0008'),
    ]
    patients = []
    for name, email, phone in PATIENTS:
        u = User(name=name, email=email, phone=phone, role='patient',
                 is_active=True, tenant_id=tid)
        u.set_password('Demo@2026!')
        sess.add(u)
        patients.append(u)
    sess.flush()

    # ── Consultas ────────────────────────────────────────────────────────────
    today      = date.today()
    times      = ['08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '14:00', '14:30', '15:00']
    APPT_TYPES = ['Consulta', 'Retorno', 'Consulta', 'Consulta', 'Retorno']

    slot = 0
    for delta in range(-14, 15):
        d = today + timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        status = ('completed' if delta % 5 != 0 else 'cancelled') if delta < 0 \
                 else ('confirmed' if delta == 0 else 'scheduled')
        for _ in range(2):
            patient   = patients[slot % len(patients)]
            prof      = profs[slot % len(profs)]
            appt_type = APPT_TYPES[slot % len(APPT_TYPES)]
            t         = times[slot % len(times)]
            pay_type  = 'convenio' if slot % 3 == 0 else 'particular'
            plan_id   = plans[0].id if pay_type == 'convenio' else None
            price     = (plans[0].consultation_value if pay_type == 'convenio' else 200.0)
            sess.add(Appointment(
                patient_id=patient.id, professional_id=prof.id,
                date=d, time=t, duration=30,
                status=status, type=appt_type,
                payment_type=pay_type, plan_id=plan_id,
                price=price, is_paid=(delta < 0),
            ))
            slot += 1
    sess.commit()


@internal_bp.route('/tenant/<slug>', methods=['DELETE'])
def deprovision(slug):
    """Remove o DB do tenant (apaga o arquivo)."""
    if not _auth():
        return _resp(error='Não autorizado', status=401)

    from database.tenant_db import remove_db
    try:
        remove_db(slug)
        return _resp()
    except OSError as e:
        return _resp(error=str(e), status=500)
