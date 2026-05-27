"""API REST v1 — consumida pelo frontend JS."""
import jwt as pyjwt
from datetime import datetime, date, timedelta
from datetime import datetime as _dt
from functools import wraps
from flask import Blueprint, jsonify, request, current_app, g
from flask_login import login_required, current_user
from database.models import Appointment, Professional, Schedule, User

api_bp = Blueprint("api", __name__)


def api_response(data=None, message="ok", status=200, error=None):
    payload = {"status": "success" if not error else "error", "message": message}
    if data is not None:
        payload["data"] = data
    if error:
        payload["error"] = error
    return jsonify(payload), status


def jwt_or_login_required(f):
    """Accepts a valid JWT Bearer token OR an active Flask-Login session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth[7:]
            try:
                payload = pyjwt.decode(
                    token,
                    current_app.config['SECRET_KEY'],
                    algorithms=['HS256']
                )
                user = g.db.query(User).get(payload['sub']) if g.db else None
                if not user or not user.is_active:
                    return api_response(error='Token inválido', status=401)
                g._jwt_user = user
            except pyjwt.ExpiredSignatureError:
                return api_response(error='Token expirado', status=401)
            except Exception:
                return api_response(error='Token inválido', status=401)
        else:
            if not current_user.is_authenticated:
                return api_response(error='Autenticação necessária', status=401)
        return f(*args, **kwargs)
    return decorated


# ─── AUTH TOKEN ──────────────────────────────────────────────────────────────

@api_bp.route('/auth/token', methods=['POST'])
def get_token():
    """Issue a JWT for API clients."""
    data     = request.get_json() or {}
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    user = g.db.query(User).filter_by(email=email).first() if g.db else None
    if not user or not user.check_password(password) or not user.is_active:
        return api_response(error='Credenciais inválidas', status=401)
    if user.role == 'patient':
        return api_response(error='Acesso não permitido', status=403)

    payload = {
        'sub':   user.id,
        'email': user.email,
        'role':  user.role,
        'exp':   _dt.utcnow() + timedelta(hours=24),
        'iat':   _dt.utcnow(),
    }
    token = pyjwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return api_response({'token': token, 'expires_in': 86400, 'user': user.to_dict()}, status=200)


# ─── HORÁRIOS DISPONÍVEIS ────────────────────────────────────────────────────

@api_bp.route("/horarios-disponiveis")
@login_required
def available_slots():
    professional_id = request.args.get("professional_id", type=int)
    date_str        = request.args.get("date")

    if not professional_id or not date_str:
        return api_response(error="professional_id e date são obrigatórios", status=400)

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return api_response(error="Formato de data inválido (YYYY-MM-DD)", status=400)

    if target_date < date.today():
        return api_response([], "Nenhum horário disponível")

    day_of_week = target_date.weekday()
    schedule = (g.db.query(Schedule)
                .filter_by(professional_id=professional_id,
                           day_of_week=day_of_week,
                           is_active=True)
                .first()) if g.db else None

    if schedule:
        start_t, end_t, slot_dur = schedule.start_time, schedule.end_time, schedule.slot_duration
    else:
        start_t, end_t, slot_dur = "08:00", "18:00", 30

    booked = set()
    if g.db:
        booked = {a.time for a in g.db.query(Appointment)
                  .filter_by(professional_id=professional_id, date=target_date)
                  .filter(Appointment.status.in_(["scheduled", "confirmed"]))
                  .all()}

    slots     = _generate_slots(start_t, end_t, slot_dur)
    available = [s for s in slots if s not in booked]

    return api_response(available)


def _generate_slots(start, end, duration):
    slots = []
    h, m   = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    current     = h * 60 + m
    end_minutes = eh * 60 + em
    while current + duration <= end_minutes:
        slots.append(f"{current // 60:02d}:{current % 60:02d}")
        current += duration
    return slots


# ─── PROFISSIONAIS ────────────────────────────────────────────────────────────

@api_bp.route("/profissionais")
@login_required
def professionals_list():
    profs = g.db.query(Professional).filter_by(is_active=True).all() if g.db else []
    return api_response([p.to_dict() for p in profs])


# ─── BUSCA DE PACIENTES (admin) ───────────────────────────────────────────────

@api_bp.route("/admin/buscar-pacientes")
@login_required
def search_patients():
    if not current_user.is_admin():
        return api_response(error="Acesso negado", status=403)
    q        = request.args.get("q", "")
    patients = (g.db.query(User)
                .filter(
                    User.role == "patient",
                    (User.name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
                )
                .limit(10)
                .all()) if g.db else []
    return api_response([{"id": p.id, "name": p.name, "email": p.email} for p in patients])


# ─── WHATSAPP REDIRECT ───────────────────────────────────────────────────────

@api_bp.route("/whatsapp/<string:phone>")
@login_required
def whatsapp_redirect(phone):
    number = "".join(filter(str.isdigit, phone))
    if not number.startswith("55"):
        number = "55" + number
    url = f"https://wa.me/{number}"
    return api_response({"url": url})
