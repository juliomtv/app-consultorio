import os
from datetime import datetime, date, timedelta
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_from_directory, abort, jsonify)
from flask_login import login_required, current_user
from database import db
from database.models import (User, Appointment, Professional, Document,
                              LibraryItem, Notification, ContractionSession,
                              Contraction, BirthPlan, AppointmentHistory, SystemLog,
                              HealthPlan)
from werkzeug.utils import secure_filename

patient_bp = Blueprint("patient", __name__)


def patient_only(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def log_action(action, details=None):
    log = SystemLog(
        user_id=current_user.id,
        action=action,
        entity="patient",
        entity_id=current_user.id,
        details=details,
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()


@patient_bp.route("/dashboard")
@login_required
@patient_only
def dashboard():
    upcoming = (Appointment.query
                .filter_by(patient_id=current_user.id)
                .filter(Appointment.date >= date.today())
                .filter(Appointment.status.in_(["scheduled", "confirmed"]))
                .order_by(Appointment.date, Appointment.time)
                .limit(5).all())

    total_appointments = Appointment.query.filter_by(patient_id=current_user.id).count()
    unread_notifications = (Notification.query
                            .filter_by(user_id=current_user.id, is_read=False)
                            .count())
    recent_docs = (Document.query
                   .filter_by(user_id=current_user.id)
                   .order_by(Document.created_at.desc())
                   .limit(3).all())

    return render_template("patient/dashboard.html",
                           upcoming=upcoming,
                           total_appointments=total_appointments,
                           unread_notifications=unread_notifications,
                           recent_docs=recent_docs)


@patient_bp.route("/consultas")
@login_required
@patient_only
def appointments():
    status_filter = request.args.get("status", "all")
    query = Appointment.query.filter_by(patient_id=current_user.id)

    if status_filter == "upcoming":
        query = query.filter(Appointment.date >= date.today(),
                             Appointment.status.in_(["scheduled", "confirmed"]))
    elif status_filter == "past":
        query = query.filter(
            (Appointment.date < date.today()) |
            (Appointment.status.in_(["completed", "cancelled", "no_show"]))
        )
    elif status_filter != "all":
        query = query.filter_by(status=status_filter)

    appointments_list = query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template("patient/appointments.html",
                           appointments=appointments_list,
                           status_filter=status_filter)


@patient_bp.route("/agendar", methods=["GET", "POST"])
@login_required
@patient_only
def schedule():
    professionals = Professional.query.filter_by(is_active=True).all()
    plans = HealthPlan.query.filter_by(is_active=True).order_by(HealthPlan.name).all()

    if request.method == "POST":
        professional_id = request.form.get("professional_id")
        date_str = request.form.get("date")
        time_str = request.form.get("time")
        notes = request.form.get("notes", "")
        appt_type = request.form.get("type", "Consulta")
        payment_type = request.form.get("payment_type", "particular")
        plan_id = request.form.get("plan_id") or None
        duration = 30

        errors = []
        if not professional_id:
            errors.append("Selecione um profissional.")
        if not date_str:
            errors.append("Selecione uma data.")
        if not time_str:
            errors.append("Selecione um horário.")

        if not errors:
            appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if appt_date < date.today():
                errors.append("Não é possível agendar para datas passadas.")

        if not errors:
            conflict = Appointment.query.filter_by(
                professional_id=professional_id,
                date=appt_date,
                time=time_str,
                status="scheduled"
            ).first()
            if conflict:
                errors.append("Este horário já está ocupado.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("patient/schedule.html", professionals=professionals, plans=plans)

        prof = Professional.query.get(professional_id)
        # Preenche preço padrão do plano se for convênio
        price = 0.0
        if payment_type == "convenio" and plan_id:
            p = HealthPlan.query.get(plan_id)
            if p:
                price = p.consultation_value

        appt = Appointment(
            patient_id=current_user.id,
            professional_id=professional_id,
            date=appt_date,
            time=time_str,
            duration=duration,
            status="scheduled",
            type=appt_type,
            payment_type=payment_type,
            plan_id=int(plan_id) if plan_id else None,
            notes=notes,
            price=price,
        )
        db.session.add(appt)
        db.session.flush()

        history = AppointmentHistory(
            appointment_id=appt.id,
            changed_by=current_user.id,
            action="created",
            new_date=appt_date,
            new_time=time_str,
            new_status="scheduled",
        )
        db.session.add(history)

        notif = Notification(
            user_id=current_user.id,
            title="Consulta agendada!",
            message=f"Sua consulta foi agendada para {appt_date.strftime('%d/%m/%Y')} às {time_str}.",
            type="appointment",
            appointment_id=appt.id,
        )
        db.session.add(notif)
        db.session.commit()
        log_action("schedule_appointment", details=f"Agendamento {appt.id}")

        flash("Consulta agendada com sucesso!", "success")
        return redirect(url_for("patient.appointments"))

    return render_template("patient/schedule.html", professionals=professionals, plans=plans)


@patient_bp.route("/reagendar/<int:appt_id>", methods=["GET", "POST"])
@login_required
@patient_only
def reschedule(appt_id):
    appt = Appointment.query.filter_by(id=appt_id, patient_id=current_user.id).first_or_404()
    if appt.status not in ("scheduled", "confirmed"):
        flash("Esta consulta não pode ser reagendada.", "warning")
        return redirect(url_for("patient.appointments"))

    if request.method == "POST":
        date_str = request.form.get("date")
        time_str = request.form.get("time")

        appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        old_date, old_time = appt.date, appt.time

        history = AppointmentHistory(
            appointment_id=appt.id,
            changed_by=current_user.id,
            action="rescheduled",
            old_date=old_date,
            new_date=appt_date,
            old_time=old_time,
            new_time=time_str,
            old_status=appt.status,
            new_status="scheduled",
        )
        appt.date = appt_date
        appt.time = time_str
        appt.status = "scheduled"
        db.session.add(history)
        db.session.commit()
        flash("Consulta reagendada com sucesso!", "success")
        return redirect(url_for("patient.appointments"))

    return render_template("patient/reschedule.html", appt=appt)


@patient_bp.route("/cancelar/<int:appt_id>", methods=["POST"])
@login_required
@patient_only
def cancel_appointment(appt_id):
    appt = Appointment.query.filter_by(id=appt_id, patient_id=current_user.id).first_or_404()
    if appt.status not in ("scheduled", "confirmed"):
        flash("Esta consulta não pode ser cancelada.", "warning")
        return redirect(url_for("patient.appointments"))

    reason = request.form.get("reason", "Cancelado pelo paciente")
    history = AppointmentHistory(
        appointment_id=appt.id,
        changed_by=current_user.id,
        action="cancelled",
        old_status=appt.status,
        new_status="cancelled",
        notes=reason,
    )
    appt.status = "cancelled"
    appt.cancellation_reason = reason
    appt.cancelled_by = "patient"
    db.session.add(history)
    db.session.commit()
    flash("Consulta cancelada.", "info")
    return redirect(url_for("patient.appointments"))


@patient_bp.route("/documentos")
@login_required
@patient_only
def documents():
    category = request.args.get("category", "all")
    query = Document.query.filter_by(user_id=current_user.id, is_visible_to_patient=True)
    if category != "all":
        query = query.filter_by(category=category)
    docs = query.order_by(Document.created_at.desc()).all()
    return render_template("patient/documents.html", documents=docs, category=category)


@patient_bp.route("/documentos/upload", methods=["POST"])
@login_required
@patient_only
def upload_document():
    if "file" not in request.files:
        flash("Nenhum arquivo enviado.", "danger")
        return redirect(url_for("patient.documents"))

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        flash("Arquivo inválido. Permitidos: PDF, PNG, JPG, DOC, DOCX.", "danger")
        return redirect(url_for("patient.documents"))

    filename = secure_filename(file.filename)
    unique_name = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    filepath = os.path.join(current_app.config["DOCUMENTS_FOLDER"], unique_name)
    file.save(filepath)

    doc = Document(
        user_id=current_user.id,
        filename=unique_name,
        original_name=file.filename,
        file_type=filename.rsplit(".", 1)[-1].lower(),
        file_size=os.path.getsize(filepath),
        category=request.form.get("category", "geral"),
        description=request.form.get("description", ""),
        uploaded_by=current_user.id,
    )
    db.session.add(doc)
    db.session.commit()
    flash("Documento enviado com sucesso!", "success")
    return redirect(url_for("patient.documents"))


@patient_bp.route("/documentos/visualizar/<int:doc_id>")
@login_required
@patient_only
def view_document(doc_id):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    return send_from_directory(current_app.config["DOCUMENTS_FOLDER"], doc.filename)


@patient_bp.route("/biblioteca")
@login_required
@patient_only
def library():
    category = request.args.get("category", "all")
    query = LibraryItem.query.filter_by(is_public=True)
    if category != "all":
        query = query.filter_by(category=category)
    items = query.order_by(LibraryItem.created_at.desc()).all()
    categories = db.session.query(LibraryItem.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template("patient/library.html", items=items,
                           categories=categories, current_category=category)


@patient_bp.route("/biblioteca/visualizar/<int:item_id>")
@login_required
@patient_only
def view_library_item(item_id):
    item = LibraryItem.query.filter_by(id=item_id, is_public=True).first_or_404()
    item.download_count += 1
    db.session.commit()
    return send_from_directory(current_app.config["LIBRARY_FOLDER"], item.filename)


@patient_bp.route("/notificacoes")
@login_required
@patient_only
def notifications():
    notifs = (Notification.query
              .filter_by(user_id=current_user.id)
              .order_by(Notification.created_at.desc())
              .all())
    return render_template("patient/notifications.html", notifications=notifs)


@patient_bp.route("/notificacoes/marcar-lida/<int:notif_id>", methods=["POST"])
@login_required
@patient_only
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"ok": True})


@patient_bp.route("/notificacoes/marcar-todas-lidas", methods=["POST"])
@login_required
@patient_only
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})


@patient_bp.route("/perfil", methods=["GET", "POST"])
@login_required
@patient_only
def profile():
    if request.method == "POST":
        current_user.name = request.form.get("name", current_user.name).strip()
        current_user.phone = request.form.get("phone", current_user.phone)
        current_user.whatsapp = request.form.get("whatsapp", current_user.whatsapp)
        current_user.address = request.form.get("address", current_user.address)
        current_user.blood_type = request.form.get("blood_type", current_user.blood_type)
        current_user.allergies = request.form.get("allergies", current_user.allergies)

        birth_str = request.form.get("birth_date", "")
        if birth_str:
            try:
                current_user.birth_date = datetime.strptime(birth_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        new_password = request.form.get("new_password", "")
        if new_password:
            if len(new_password) < 8:
                flash("Nova senha deve ter pelo menos 8 caracteres.", "danger")
                return redirect(url_for("patient.profile"))
            current_user.set_password(new_password)

        db.session.commit()
        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for("patient.profile"))

    return render_template("patient/profile.html")


@patient_bp.route("/contracoes")
@login_required
@patient_only
def contractions():
    sessions = (ContractionSession.query
                .filter_by(user_id=current_user.id)
                .order_by(ContractionSession.started_at.desc())
                .limit(10).all())
    return render_template("patient/contractions.html", sessions=sessions)


@patient_bp.route("/plano-de-parto", methods=["GET", "POST"])
@login_required
@patient_only
def birth_plan():
    plan = BirthPlan.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        if not plan:
            plan = BirthPlan(user_id=current_user.id)
            db.session.add(plan)

        plan.hospital = request.form.get("hospital", "")
        plan.doctor_name = request.form.get("doctor_name", "")
        plan.birth_type_preference = request.form.get("birth_type_preference", "")
        plan.companion_name = request.form.get("companion_name", "")
        plan.companion_relation = request.form.get("companion_relation", "")
        plan.pain_management = request.form.get("pain_management", "")
        plan.labor_preferences = request.form.get("labor_preferences", "")
        plan.delivery_preferences = request.form.get("delivery_preferences", "")
        plan.postpartum_preferences = request.form.get("postpartum_preferences", "")
        plan.breastfeeding = request.form.get("breastfeeding") == "on"
        plan.skin_to_skin = request.form.get("skin_to_skin") == "on"
        plan.cord_clamping = request.form.get("cord_clamping", "delayed")
        plan.cord_blood_collection = request.form.get("cord_blood_collection") == "on"
        plan.photos_allowed = request.form.get("photos_allowed") == "on"
        plan.additional_notes = request.form.get("additional_notes", "")

        db.session.commit()
        flash("Plano de parto salvo com sucesso!", "success")
        return redirect(url_for("patient.birth_plan"))

    return render_template("patient/birth_plan.html", plan=plan)
