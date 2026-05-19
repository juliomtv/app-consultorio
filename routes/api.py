"""API REST v1 — consumida pelo frontend JS e futuramente pelo app mobile."""
from datetime import datetime, date, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from database import db
from database.models import (Appointment, Professional, Schedule, Notification,
                              ContractionSession, Contraction, User)

api_bp = Blueprint("api", __name__)


def api_response(data=None, message="ok", status=200, error=None):
    payload = {"status": "success" if not error else "error", "message": message}
    if data is not None:
        payload["data"] = data
    if error:
        payload["error"] = error
    return jsonify(payload), status


# ─── HORÁRIOS DISPONÍVEIS ────────────────────────────────────────────────────

@api_bp.route("/horarios-disponiveis")
@login_required
def available_slots():
    professional_id = request.args.get("professional_id", type=int)
    date_str = request.args.get("date")

    if not professional_id or not date_str:
        return api_response(error="professional_id e date são obrigatórios", status=400)

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return api_response(error="Formato de data inválido (YYYY-MM-DD)", status=400)

    if target_date < date.today():
        return api_response([], "Nenhum horário disponível")

    day_of_week = target_date.weekday()  # 0=Mon
    schedule = Schedule.query.filter_by(
        professional_id=professional_id,
        day_of_week=day_of_week,
        is_active=True
    ).first()

    # Se não há agenda cadastrada, usa horário padrão 08:00–18:00
    if schedule:
        start_t, end_t, slot_dur = schedule.start_time, schedule.end_time, schedule.slot_duration
    else:
        start_t, end_t, slot_dur = "08:00", "18:00", 30

    booked = {a.time for a in Appointment.query.filter_by(
        professional_id=professional_id,
        date=target_date,
    ).filter(Appointment.status.in_(["scheduled", "confirmed"])).all()}

    slots = _generate_slots(start_t, end_t, slot_dur)
    available = [s for s in slots if s not in booked]

    return api_response(available)


def _generate_slots(start, end, duration):
    slots = []
    h, m = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    current = h * 60 + m
    end_minutes = eh * 60 + em
    while current + duration <= end_minutes:
        slots.append(f"{current // 60:02d}:{current % 60:02d}")
        current += duration
    return slots


# ─── NOTIFICAÇÕES ────────────────────────────────────────────────────────────

@api_bp.route("/notificacoes")
@login_required
def notifications():
    notifs = (Notification.query
              .filter_by(user_id=current_user.id)
              .order_by(Notification.created_at.desc())
              .limit(20).all())
    return api_response([n.to_dict() for n in notifs])


@api_bp.route("/notificacoes/nao-lidas")
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return api_response({"count": count})


@api_bp.route("/notificacoes/<int:notif_id>/lida", methods=["POST"])
@login_required
def mark_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return api_response(message="Marcado como lido")


# ─── CONTRAÇÕES ──────────────────────────────────────────────────────────────

@api_bp.route("/contracoes/sessao", methods=["POST"])
@login_required
def start_contraction_session():
    session = ContractionSession(user_id=current_user.id)
    db.session.add(session)
    db.session.commit()
    return api_response({"session_id": session.id}, "Sessão iniciada", 201)


@api_bp.route("/contracoes/sessao/<int:session_id>/encerrar", methods=["POST"])
@login_required
def end_contraction_session(session_id):
    session = ContractionSession.query.filter_by(
        id=session_id, user_id=current_user.id).first_or_404()
    session.ended_at = datetime.utcnow()
    session.notes = request.json.get("notes", "") if request.is_json else ""

    contractions = session.contractions.all()
    session.total_contractions = len(contractions)
    if contractions:
        durations = [c.duration for c in contractions if c.duration]
        intervals = [c.interval for c in contractions if c.interval]
        session.avg_duration = sum(durations) / len(durations) if durations else None
        session.avg_interval = sum(intervals) / len(intervals) if intervals else None

    db.session.commit()
    return api_response(session.to_dict())


@api_bp.route("/contracoes/sessao/<int:session_id>/registrar", methods=["POST"])
@login_required
def register_contraction(session_id):
    session = ContractionSession.query.filter_by(
        id=session_id, user_id=current_user.id).first_or_404()

    data = request.get_json() or {}
    started_at = datetime.fromisoformat(data.get("started_at", datetime.utcnow().isoformat()))
    ended_at_str = data.get("ended_at")
    ended_at = datetime.fromisoformat(ended_at_str) if ended_at_str else None
    duration = data.get("duration")
    interval = data.get("interval")

    contraction = Contraction(
        session_id=session_id,
        started_at=started_at,
        ended_at=ended_at,
        duration=duration,
        interval=interval,
        intensity=data.get("intensity"),
    )
    db.session.add(contraction)
    db.session.commit()
    return api_response(contraction.to_dict(), status=201)


@api_bp.route("/contracoes/sessao/<int:session_id>")
@login_required
def get_session(session_id):
    session = ContractionSession.query.filter_by(
        id=session_id, user_id=current_user.id).first_or_404()
    contractions = [c.to_dict() for c in session.contractions.order_by(Contraction.started_at).all()]
    result = session.to_dict()
    result["contractions"] = contractions
    return api_response(result)


# ─── PROFISSIONAIS ────────────────────────────────────────────────────────────

@api_bp.route("/profissionais")
@login_required
def professionals_list():
    profs = Professional.query.filter_by(is_active=True).all()
    return api_response([p.to_dict() for p in profs])


# ─── CONSULTAS ───────────────────────────────────────────────────────────────

@api_bp.route("/consultas/proximas")
@login_required
def upcoming_appointments():
    appts = (Appointment.query
             .filter_by(patient_id=current_user.id)
             .filter(Appointment.date >= date.today())
             .filter(Appointment.status.in_(["scheduled", "confirmed"]))
             .order_by(Appointment.date, Appointment.time)
             .limit(5).all())
    return api_response([a.to_dict() for a in appts])


# ─── BUSCA DE PACIENTES (admin) ───────────────────────────────────────────────

@api_bp.route("/admin/buscar-pacientes")
@login_required
def search_patients():
    if not current_user.is_admin():
        return api_response(error="Acesso negado", status=403)
    q = request.args.get("q", "")
    patients = User.query.filter(
        User.role == "patient",
        (User.name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
    ).limit(10).all()
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
