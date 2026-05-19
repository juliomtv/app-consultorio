import os
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_from_directory, jsonify)
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from database import db
from database.models import (User, Professional, Appointment, Document,
                              LibraryItem, Notification, FinancialTransaction,
                              Schedule, SystemLog, AppointmentHistory,
                              HealthPlan, InsuranceGuide)
from werkzeug.utils import secure_filename

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash("Acesso restrito à administração.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename, allowed=None):
    if allowed is None:
        allowed = current_app.config["ALLOWED_EXTENSIONS"]
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in allowed


def log_action(action, entity=None, entity_id=None, details=None, status="success"):
    log = SystemLog(
        user_id=current_user.id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:255],
        status=status,
    )
    db.session.add(log)
    db.session.commit()


# ─── DASHBOARD ─────────────────────────────────────────────────────────────

@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)

    stats = {
        "total_patients": User.query.filter_by(role="patient").count(),
        "total_appointments": Appointment.query.count(),
        "today_appointments": Appointment.query.filter_by(date=today).count(),
        "month_appointments": Appointment.query.filter(Appointment.date >= month_start).count(),
        "pending_appointments": Appointment.query.filter_by(status="scheduled").count(),
        "month_revenue": db.session.query(func.sum(FinancialTransaction.amount))
            .filter(FinancialTransaction.type == "income",
                    FinancialTransaction.status == "paid",
                    FinancialTransaction.paid_at >= month_start).scalar() or 0,
        "new_patients_month": User.query.filter(
            User.role == "patient",
            User.created_at >= month_start
        ).count(),
    }

    today_appts = (Appointment.query
                   .filter_by(date=today)
                   .order_by(Appointment.time)
                   .all())

    recent_patients = (User.query
                       .filter_by(role="patient")
                       .order_by(User.created_at.desc())
                       .limit(5).all())

    monthly_data = _get_monthly_chart_data()

    return render_template("admin/dashboard.html",
                           stats=stats,
                           today_appts=today_appts,
                           recent_patients=recent_patients,
                           monthly_data=monthly_data)


def _get_monthly_chart_data():
    today = date.today()
    data = []
    for i in range(6):
        month = (today.replace(day=1) - timedelta(days=i * 30))
        count = Appointment.query.filter(
            extract("month", Appointment.date) == month.month,
            extract("year", Appointment.date) == month.year
        ).count()
        data.append({"month": month.strftime("%b/%y"), "count": count})
    return list(reversed(data))


# ─── PACIENTES ─────────────────────────────────────────────────────────────

@admin_bp.route("/pacientes")
@login_required
@admin_required
def patients():
    search = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    query = User.query.filter_by(role="patient")

    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.cpf.ilike(f"%{search}%")) |
            (User.phone.ilike(f"%{search}%"))
        )

    patients_page = query.order_by(User.name).paginate(page=page, per_page=20)
    return render_template("admin/patients.html",
                           patients=patients_page, search=search)


@admin_bp.route("/pacientes/<int:patient_id>")
@login_required
@admin_required
def patient_detail(patient_id):
    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()
    appointments = (Appointment.query
                    .filter_by(patient_id=patient_id)
                    .order_by(Appointment.date.desc())
                    .all())
    documents = (Document.query
                 .filter_by(user_id=patient_id)
                 .order_by(Document.created_at.desc())
                 .all())
    return render_template("admin/patient_detail.html",
                           patient=patient, appointments=appointments,
                           documents=documents)


@admin_bp.route("/pacientes/novo", methods=["GET", "POST"])
@login_required
@admin_required
def new_patient():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "")
        cpf = request.form.get("cpf", "")
        birth_date_str = request.form.get("birth_date", "")

        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "danger")
            return render_template("admin/patient_form.html")

        user = User(name=name, email=email, phone=phone,
                    cpf=cpf or None, role="patient")
        user.set_password(secrets_token())
        if birth_date_str:
            try:
                user.birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        db.session.add(user)
        db.session.commit()
        log_action("create_patient", "user", user.id, f"Novo paciente: {name}")
        flash("Paciente cadastrado com sucesso!", "success")
        return redirect(url_for("admin.patients"))

    return render_template("admin/patient_form.html")


@admin_bp.route("/pacientes/editar/<int:patient_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_patient(patient_id):
    patient = User.query.filter_by(id=patient_id).first_or_404()

    if request.method == "POST":
        patient.name = request.form.get("name", patient.name).strip()
        patient.phone = request.form.get("phone", patient.phone)
        patient.whatsapp = request.form.get("whatsapp", patient.whatsapp)
        patient.cpf = request.form.get("cpf", patient.cpf) or None
        patient.address = request.form.get("address", patient.address)
        patient.blood_type = request.form.get("blood_type", patient.blood_type)
        patient.allergies = request.form.get("allergies", patient.allergies)
        patient.observations = request.form.get("observations", patient.observations)
        patient.is_active = request.form.get("is_active") == "on"
        db.session.commit()
        log_action("edit_patient", "user", patient_id, f"Editou: {patient.name}")
        flash("Paciente atualizado!", "success")
        return redirect(url_for("admin.patient_detail", patient_id=patient_id))

    return render_template("admin/patient_form.html", patient=patient)


# ─── PROFISSIONAIS ──────────────────────────────────────────────────────────

@admin_bp.route("/profissionais")
@login_required
@admin_required
def professionals():
    profs = Professional.query.join(User).filter(User.is_active == True).all()
    return render_template("admin/professionals.html", professionals=profs)


@admin_bp.route("/profissionais/novo", methods=["GET", "POST"])
@login_required
@admin_required
def new_professional():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        specialty = request.form.get("specialty", "")
        council_type = request.form.get("council_type", "")
        council_number = request.form.get("council_number", "")

        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "danger")
            return render_template("admin/professional_form.html")

        user = User(name=name, email=email, role="professional")
        user.set_password(secrets_token())
        db.session.add(user)
        db.session.flush()

        prof = Professional(user_id=user.id, specialty=specialty,
                            council_type=council_type, council_number=council_number)
        db.session.add(prof)
        db.session.commit()
        log_action("create_professional", "professional", prof.id)
        flash("Profissional cadastrado!", "success")
        return redirect(url_for("admin.professionals"))

    return render_template("admin/professional_form.html")


# ─── CONSULTAS ──────────────────────────────────────────────────────────────

@admin_bp.route("/consultas")
@login_required
@admin_required
def appointments():
    return redirect(url_for("admin.schedule"))



@admin_bp.route("/consultas/<int:appt_id>/status", methods=["POST"])
@login_required
@admin_required
def update_appointment_status(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    new_status = request.form.get("status")
    valid_statuses = ("scheduled", "confirmed", "cancelled", "completed", "no_show")
    if new_status not in valid_statuses:
        flash("Status inválido.", "danger")
        return redirect(url_for("admin.appointments"))

    history = AppointmentHistory(
        appointment_id=appt.id,
        changed_by=current_user.id,
        action=new_status,
        old_status=appt.status,
        new_status=new_status,
    )
    appt.status = new_status
    if new_status == "confirmed":
        notif = Notification(
            user_id=appt.patient_id,
            title="Consulta confirmada!",
            message=f"Sua consulta em {appt.date.strftime('%d/%m/%Y')} às {appt.time} foi confirmada.",
            type="success",
            appointment_id=appt.id,
        )
        db.session.add(notif)
    db.session.add(history)
    db.session.commit()
    log_action("update_appointment", "appointment", appt_id, f"Status: {new_status}")
    flash(f"Status atualizado para '{new_status}'.", "success")
    return redirect(request.referrer or url_for("admin.appointments"))


@admin_bp.route("/agenda")
@login_required
@admin_required
def schedule():
    date_str = request.args.get("date", date.today().isoformat())
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = date.today()

    professional_filter = request.args.get("professional_id", "all")
    professionals = Professional.query.filter_by(is_active=True).all()

    query = Appointment.query.filter_by(date=selected_date)
    if professional_filter != "all":
        try:
            query = query.filter_by(professional_id=int(professional_filter))
        except ValueError:
            pass

    appointments_day = query.order_by(Appointment.time).all()

    appts_by_prof = {}
    for appt in appointments_day:
        appts_by_prof.setdefault(appt.professional_id, []).append(appt)

    return render_template("admin/schedule.html",
                           professionals=professionals,
                           appts_by_prof=appts_by_prof,
                           selected_date=selected_date,
                           professional_filter=professional_filter,
                           now=selected_date)


# ─── FINANCEIRO ─────────────────────────────────────────────────────────────

@admin_bp.route("/financeiro")
@login_required
@admin_required
def financial():
    page = request.args.get("page", 1, type=int)
    type_filter = request.args.get("type", "all")
    month_filter = request.args.get("month", date.today().strftime("%Y-%m"))

    query = FinancialTransaction.query
    if type_filter != "all":
        query = query.filter_by(type=type_filter)

    if month_filter:
        try:
            y, m = month_filter.split("-")
            query = query.filter(
                extract("year", FinancialTransaction.created_at) == int(y),
                extract("month", FinancialTransaction.created_at) == int(m),
            )
        except (ValueError, AttributeError):
            pass

    transactions = query.order_by(FinancialTransaction.created_at.desc()).paginate(page=page, per_page=25)

    totals = {
        "income": db.session.query(func.sum(FinancialTransaction.amount))
            .filter_by(type="income", status="paid").scalar() or 0,
        "expense": db.session.query(func.sum(FinancialTransaction.amount))
            .filter_by(type="expense", status="paid").scalar() or 0,
    }
    totals["balance"] = totals["income"] - totals["expense"]

    return render_template("admin/financial.html",
                           transactions=transactions,
                           totals=totals,
                           type_filter=type_filter,
                           month_filter=month_filter)


@admin_bp.route("/financeiro/novo", methods=["POST"])
@login_required
@admin_required
def new_transaction():
    t = FinancialTransaction(
        type=request.form.get("type"),
        category=request.form.get("category"),
        description=request.form.get("description"),
        amount=float(request.form.get("amount", 0)),
        payment_method=request.form.get("payment_method"),
        status=request.form.get("status", "pending"),
        notes=request.form.get("notes"),
        created_by=current_user.id,
    )
    if request.form.get("due_date"):
        t.due_date = datetime.strptime(request.form["due_date"], "%Y-%m-%d").date()
    if t.status == "paid":
        t.paid_at = datetime.utcnow()
    db.session.add(t)
    db.session.commit()
    flash("Transação registrada!", "success")
    return redirect(url_for("admin.financial"))


# ─── BIBLIOTECA ─────────────────────────────────────────────────────────────

@admin_bp.route("/biblioteca")
@login_required
@admin_required
def library():
    items = LibraryItem.query.order_by(LibraryItem.created_at.desc()).all()
    return render_template("admin/library.html", items=items)


@admin_bp.route("/biblioteca/upload", methods=["POST"])
@login_required
@admin_required
def upload_library_item():
    if "file" not in request.files:
        flash("Nenhum arquivo enviado.", "danger")
        return redirect(url_for("admin.library"))

    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename, {"pdf", "epub"}):
        flash("Apenas PDF ou EPUB são permitidos.", "danger")
        return redirect(url_for("admin.library"))

    filename = secure_filename(file.filename)
    unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    filepath = os.path.join(current_app.config["LIBRARY_FOLDER"], unique_name)
    file.save(filepath)

    item = LibraryItem(
        title=request.form.get("title", filename),
        description=request.form.get("description", ""),
        filename=unique_name,
        category=request.form.get("category", "Geral"),
        tags=request.form.get("tags", ""),
        file_size=os.path.getsize(filepath),
        is_public=request.form.get("is_public") == "on",
        uploaded_by=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    log_action("upload_library", "library", item.id, f"Upload: {item.title}")
    flash("Material adicionado à biblioteca!", "success")
    return redirect(url_for("admin.library"))


@admin_bp.route("/biblioteca/excluir/<int:item_id>", methods=["POST"])
@login_required
@admin_required
def delete_library_item(item_id):
    item = LibraryItem.query.get_or_404(item_id)
    filepath = os.path.join(current_app.config["LIBRARY_FOLDER"], item.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(item)
    db.session.commit()
    flash("Item removido.", "info")
    return redirect(url_for("admin.library"))


@admin_bp.route("/biblioteca/arquivo/<int:item_id>")
@login_required
@admin_required
def serve_library_file(item_id):
    item = LibraryItem.query.get_or_404(item_id)
    return send_from_directory(current_app.config["LIBRARY_FOLDER"], item.filename)


# ─── LOGS ───────────────────────────────────────────────────────────────────

@admin_bp.route("/logs")
@login_required
@admin_required
def logs():
    page = request.args.get("page", 1, type=int)
    action_filter = request.args.get("action", "")
    query = SystemLog.query
    if action_filter:
        query = query.filter(SystemLog.action.ilike(f"%{action_filter}%"))
    logs_page = query.order_by(SystemLog.created_at.desc()).paginate(page=page, per_page=50)
    return render_template("admin/logs.html", logs=logs_page, action_filter=action_filter)


# ─── DOCUMENTOS DO PACIENTE (admin) ─────────────────────────────────────────

@admin_bp.route("/documentos/upload/<int:patient_id>", methods=["POST"])
@login_required
@admin_required
def upload_patient_document(patient_id):
    patient = User.query.get_or_404(patient_id)
    file = request.files.get("file")
    if not file or not allowed_file(file.filename):
        flash("Arquivo inválido.", "danger")
        return redirect(url_for("admin.patient_detail", patient_id=patient_id))

    filename = secure_filename(file.filename)
    unique_name = f"{patient_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    filepath = os.path.join(current_app.config["DOCUMENTS_FOLDER"], unique_name)
    file.save(filepath)

    doc = Document(
        user_id=patient_id,
        filename=unique_name,
        original_name=file.filename,
        file_type=filename.rsplit(".", 1)[-1].lower(),
        file_size=os.path.getsize(filepath),
        category=request.form.get("category", "geral"),
        description=request.form.get("description", ""),
        uploaded_by=current_user.id,
        is_visible_to_patient=request.form.get("visible") == "on",
    )
    db.session.add(doc)
    db.session.commit()
    flash("Documento enviado!", "success")
    return redirect(url_for("admin.patient_detail", patient_id=patient_id))


@admin_bp.route("/documentos/visualizar/<int:doc_id>")
@login_required
@admin_required
def view_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    return send_from_directory(current_app.config["DOCUMENTS_FOLDER"], doc.filename)


# ─── NOTIFICAÇÕES (admin → paciente) ─────────────────────────────────────────

@admin_bp.route("/notificacoes/enviar", methods=["POST"])
@login_required
@admin_required
def send_notification():
    patient_id = request.form.get("patient_id")
    title = request.form.get("title")
    message = request.form.get("message")
    notif_type = request.form.get("type", "info")

    notif = Notification(
        user_id=patient_id,
        title=title,
        message=message,
        type=notif_type,
    )
    db.session.add(notif)
    db.session.commit()
    flash("Notificação enviada!", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


def secrets_token():
    import secrets
    return secrets.token_urlsafe(16)


# ─── CRIAR CONSULTA (admin) ───────────────────────────────────────────────────

@admin_bp.route("/agenda/nova", methods=["GET", "POST"])
@login_required
@admin_required
def new_appointment():
    professionals = Professional.query.filter_by(is_active=True).order_by(Professional.id).all()
    patients = User.query.filter_by(role="patient", is_active=True).order_by(User.name).all()
    plans = HealthPlan.query.filter_by(is_active=True).order_by(HealthPlan.name).all()

    if request.method == "POST":
        patient_id    = request.form.get("patient_id")
        prof_id       = request.form.get("professional_id")
        date_str      = request.form.get("date")
        time_str      = request.form.get("time")
        appt_type     = request.form.get("type", "Consulta")
        payment_type  = request.form.get("payment_type", "particular")
        plan_id       = request.form.get("plan_id") or None
        notes         = request.form.get("notes", "").strip()
        internal_notes= request.form.get("internal_notes", "").strip()
        price_raw     = request.form.get("price", "").strip()
        status        = request.form.get("status", "scheduled")

        errors = []
        if not patient_id:    errors.append("Selecione um paciente.")
        if not prof_id:       errors.append("Selecione um profissional.")
        if not date_str:      errors.append("Informe a data.")
        if not time_str:      errors.append("Informe o horário.")

        if not errors:
            try:
                appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Data inválida.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/appointment_form.html",
                                   professionals=professionals, patients=patients,
                                   plans=plans)

        # Preço: usa o digitado, ou valor padrão do plano
        try:
            price = float(price_raw) if price_raw else 0.0
        except ValueError:
            price = 0.0
        if price == 0.0 and payment_type == "convenio" and plan_id:
            p = HealthPlan.query.get(plan_id)
            if p:
                price = p.consultation_value

        appt = Appointment(
            patient_id=int(patient_id),
            professional_id=int(prof_id),
            date=appt_date,
            time=time_str,
            duration=30,
            status=status,
            type=appt_type,
            payment_type=payment_type,
            plan_id=int(plan_id) if plan_id else None,
            notes=notes,
            internal_notes=internal_notes,
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
            new_status=status,
        )
        db.session.add(history)

        notif = Notification(
            user_id=int(patient_id),
            title="Nova consulta agendada",
            message=f"Uma consulta foi agendada para você em {appt_date.strftime('%d/%m/%Y')} às {time_str}.",
            type="appointment",
            appointment_id=appt.id,
        )
        db.session.add(notif)
        db.session.commit()
        log_action("create_appointment", "appointment", appt.id,
                   f"Admin agendou para paciente {patient_id}")
        flash("Consulta agendada com sucesso!", "success")
        return redirect(url_for("admin.schedule", date=date_str))

    # pré-preenche data se vier da agenda
    prefill_date = request.args.get("date", date.today().isoformat())
    prefill_time = request.args.get("time", "")
    prefill_prof = request.args.get("professional_id", "")
    return render_template("admin/appointment_form.html",
                           professionals=professionals, patients=patients,
                           plans=plans, prefill_date=prefill_date,
                           prefill_time=prefill_time, prefill_prof=prefill_prof)


# ─── PLANOS DE SAÚDE ──────────────────────────────────────────────────────────

@admin_bp.route("/planos")
@login_required
@admin_required
def health_plans():
    plans = HealthPlan.query.order_by(HealthPlan.name).all()
    return render_template("admin/health_plans.html", plans=plans)


@admin_bp.route("/planos/novo", methods=["GET", "POST"])
@login_required
@admin_required
def new_health_plan():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Nome do plano é obrigatório.", "danger")
            return redirect(url_for("admin.new_health_plan"))

        plan = HealthPlan(
            name=name,
            operator=request.form.get("operator", "").strip(),
            ans_code=request.form.get("ans_code", "").strip(),
            consultation_value=float(request.form.get("consultation_value") or 0),
            notes=request.form.get("notes", "").strip(),
            is_active=True,
        )
        db.session.add(plan)
        db.session.commit()
        log_action("create_health_plan", "health_plan", plan.id, plan.name)
        flash(f"Plano '{plan.name}' cadastrado!", "success")
        return redirect(url_for("admin.health_plans"))
    return render_template("admin/health_plan_form.html", plan=None)


@admin_bp.route("/planos/<int:plan_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def edit_health_plan(plan_id):
    plan = HealthPlan.query.get_or_404(plan_id)
    if request.method == "POST":
        plan.name = request.form.get("name", plan.name).strip()
        plan.operator = request.form.get("operator", "").strip()
        plan.ans_code = request.form.get("ans_code", "").strip()
        plan.consultation_value = float(request.form.get("consultation_value") or 0)
        plan.notes = request.form.get("notes", "").strip()
        db.session.commit()
        flash("Plano atualizado!", "success")
        return redirect(url_for("admin.health_plans"))
    return render_template("admin/health_plan_form.html", plan=plan)


@admin_bp.route("/planos/<int:plan_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_health_plan(plan_id):
    plan = HealthPlan.query.get_or_404(plan_id)
    plan.is_active = not plan.is_active
    db.session.commit()
    status = "ativado" if plan.is_active else "desativado"
    flash(f"Plano '{plan.name}' {status}.", "success")
    return redirect(url_for("admin.health_plans"))


# ─── GUIAS DE PLANO ───────────────────────────────────────────────────────────

@admin_bp.route("/guias")
@login_required
@admin_required
def insurance_guides():
    status_filter = request.args.get("status", "all")
    plan_filter = request.args.get("plan_id", "all")
    page = request.args.get("page", 1, type=int)

    query = InsuranceGuide.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter)
    if plan_filter != "all":
        try:
            query = query.filter_by(plan_id=int(plan_filter))
        except ValueError:
            pass

    guides = query.order_by(InsuranceGuide.created_at.desc()).paginate(page=page, per_page=25)
    plans = HealthPlan.query.filter_by(is_active=True).order_by(HealthPlan.name).all()
    return render_template("admin/insurance_guides.html",
                           guides=guides, plans=plans,
                           status_filter=status_filter, plan_filter=plan_filter)


@admin_bp.route("/guias/nova", methods=["GET", "POST"])
@login_required
@admin_required
def new_insurance_guide():
    plans = HealthPlan.query.filter_by(is_active=True).order_by(HealthPlan.name).all()
    patients = User.query.filter_by(role="patient", is_active=True).order_by(User.name).all()

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        plan_id = request.form.get("plan_id")
        if not patient_id or not plan_id:
            flash("Paciente e plano são obrigatórios.", "danger")
            return render_template("admin/insurance_guide_form.html",
                                   plans=plans, patients=patients, guide=None)

        appt_id = request.form.get("appointment_id") or None
        expiry_str = request.form.get("expiry_date", "")
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date() if expiry_str else None

        guide = InsuranceGuide(
            patient_id=int(patient_id),
            plan_id=int(plan_id),
            appointment_id=int(appt_id) if appt_id else None,
            guide_number=request.form.get("guide_number", "").strip(),
            authorization_code=request.form.get("authorization_code", "").strip(),
            procedure_code=request.form.get("procedure_code", "").strip(),
            procedure_name=request.form.get("procedure_name", "").strip(),
            requested_value=float(request.form.get("requested_value") or 0),
            authorized_value=float(request.form.get("authorized_value") or 0),
            paid_value=float(request.form.get("paid_value") or 0),
            status=request.form.get("status", "pending"),
            expiry_date=expiry,
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(guide)
        db.session.commit()
        log_action("create_guide", "insurance_guide", guide.id)
        flash("Guia cadastrada com sucesso!", "success")
        return redirect(url_for("admin.insurance_guides"))

    appt_id = request.args.get("appointment_id")
    return render_template("admin/insurance_guide_form.html",
                           plans=plans, patients=patients,
                           guide=None, prefill_appt_id=appt_id)


@admin_bp.route("/guias/<int:guide_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def edit_insurance_guide(guide_id):
    guide = InsuranceGuide.query.get_or_404(guide_id)
    plans = HealthPlan.query.filter_by(is_active=True).order_by(HealthPlan.name).all()
    patients = User.query.filter_by(role="patient", is_active=True).order_by(User.name).all()

    if request.method == "POST":
        guide.guide_number = request.form.get("guide_number", "").strip()
        guide.authorization_code = request.form.get("authorization_code", "").strip()
        guide.procedure_code = request.form.get("procedure_code", "").strip()
        guide.procedure_name = request.form.get("procedure_name", "").strip()
        guide.requested_value = float(request.form.get("requested_value") or 0)
        guide.authorized_value = float(request.form.get("authorized_value") or 0)
        guide.paid_value = float(request.form.get("paid_value") or 0)
        guide.status = request.form.get("status", guide.status)
        guide.plan_id = int(request.form.get("plan_id", guide.plan_id))
        expiry_str = request.form.get("expiry_date", "")
        guide.expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date() if expiry_str else None
        guide.notes = request.form.get("notes", "").strip()
        db.session.commit()
        flash("Guia atualizada!", "success")
        return redirect(url_for("admin.insurance_guides"))

    return render_template("admin/insurance_guide_form.html",
                           plans=plans, patients=patients, guide=guide)
