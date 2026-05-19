from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    cpf = db.Column(db.String(14), unique=True)
    birth_date = db.Column(db.Date)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="patient")  # patient | admin | professional
    is_active = db.Column(db.Boolean, default=True)
    avatar = db.Column(db.String(255))
    whatsapp = db.Column(db.String(20))
    address = db.Column(db.String(255))
    blood_type = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    observations = db.Column(db.Text)
    reset_token = db.Column(db.String(100))
    reset_token_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    appointments = db.relationship("Appointment", foreign_keys="Appointment.patient_id", backref="patient", lazy="dynamic")
    documents = db.relationship("Document", foreign_keys="Document.user_id", backref="owner", lazy="dynamic")
    notifications = db.relationship("Notification", backref="recipient", lazy="dynamic")
    contraction_sessions = db.relationship("ContractionSession", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role in ("admin",)

    def is_professional(self):
        return self.role in ("professional", "admin")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "cpf": self.cpf,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.email}>"


class Professional(db.Model):
    __tablename__ = "professionals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    council_number = db.Column(db.String(50))  # CRM, CRO, etc.
    council_type = db.Column(db.String(10))    # CRM, CRO, CFP, etc.
    bio = db.Column(db.Text)
    consultation_duration = db.Column(db.Integer, nullable=True)  # minutos por padrão (opcional)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("professional_profile", uselist=False))
    schedules = db.relationship("Schedule", backref="professional", lazy="dynamic")
    appointments = db.relationship("Appointment", foreign_keys="Appointment.professional_id", backref="professional", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.user.name if self.user else "",
            "specialty": self.specialty,
            "council_number": self.council_number,
            "council_type": self.council_type,
            "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<Professional {self.specialty}>"


class Schedule(db.Model):
    """Disponibilidade semanal do profissional."""
    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(db.Integer, db.ForeignKey("professionals.id"), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time = db.Column(db.String(5), nullable=False)  # "08:00"
    end_time = db.Column(db.String(5), nullable=False)    # "18:00"
    slot_duration = db.Column(db.Integer, default=30)     # minutes
    is_active = db.Column(db.Boolean, default=True)
    max_patients = db.Column(db.Integer, default=1)

    def __repr__(self):
        days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        return f"<Schedule {days[self.day_of_week]} {self.start_time}-{self.end_time}>"


class HealthPlan(db.Model):
    """Planos de saúde aceitos pelo consultório."""
    __tablename__ = "health_plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    operator = db.Column(db.String(150))        # operadora (ex: Unimed, Bradesco)
    ans_code = db.Column(db.String(20))         # registro ANS
    consultation_value = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", backref="plan", lazy="dynamic")
    guides = db.relationship("InsuranceGuide", backref="plan", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "operator": self.operator,
            "ans_code": self.ans_code,
            "consultation_value": self.consultation_value,
            "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<HealthPlan {self.name}>"


class InsuranceGuide(db.Model):
    """Guias de plano de saúde vinculadas a consultas."""
    __tablename__ = "insurance_guides"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("health_plans.id"), nullable=False)
    guide_number = db.Column(db.String(50))
    authorization_code = db.Column(db.String(50))
    procedure_code = db.Column(db.String(20))   # código TUSS/CBHPM
    procedure_name = db.Column(db.String(200))
    requested_value = db.Column(db.Float, default=0.0)
    authorized_value = db.Column(db.Float, default=0.0)
    paid_value = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="pending")
    # pending | authorized | submitted | paid | denied | cancelled
    expiry_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("User", foreign_keys=[patient_id])
    guide_appointment = db.relationship("Appointment", foreign_keys=[appointment_id], backref="guide")

    def __repr__(self):
        return f"<InsuranceGuide {self.guide_number} - {self.status}>"


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey("professionals.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False)  # "14:30"
    duration = db.Column(db.Integer, default=30)    # minutes
    status = db.Column(db.String(20), default="scheduled")
    # scheduled | confirmed | cancelled | completed | no_show
    type = db.Column(db.String(50), default="Consulta")
    payment_type = db.Column(db.String(20), default="particular")  # particular | convenio | cortesia
    plan_id = db.Column(db.Integer, db.ForeignKey("health_plans.id"), nullable=True)
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    cancellation_reason = db.Column(db.Text)
    cancelled_by = db.Column(db.String(20))
    teleconsult_link = db.Column(db.String(255))
    price = db.Column(db.Float, default=0.0)
    is_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    history = db.relationship("AppointmentHistory", backref="appointment", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient.name if self.patient else "",
            "professional_id": self.professional_id,
            "professional_name": self.professional.user.name if self.professional and self.professional.user else "",
            "date": self.date.isoformat() if self.date else None,
            "time": self.time,
            "duration": self.duration,
            "status": self.status,
            "type": self.type,
            "notes": self.notes,
            "price": self.price,
            "is_paid": self.is_paid,
        }

    def __repr__(self):
        return f"<Appointment {self.date} {self.time} - {self.status}>"


class AppointmentHistory(db.Model):
    __tablename__ = "appointment_history"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(50))  # created | rescheduled | cancelled | confirmed | completed
    old_date = db.Column(db.Date)
    new_date = db.Column(db.Date)
    old_time = db.Column(db.String(5))
    new_time = db.Column(db.String(5))
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    changed_by_user = db.relationship("User", foreign_keys=[changed_by])


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"))
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255))
    file_type = db.Column(db.String(50))  # pdf | image | doc
    file_size = db.Column(db.Integer)     # bytes
    category = db.Column(db.String(50), default="geral")
    # geral | exame | receita | atestado | laudo
    description = db.Column(db.Text)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_visible_to_patient = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader = db.relationship("User", foreign_keys=[uploaded_by])

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_name": self.original_name,
            "file_type": self.file_type,
            "category": self.category,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LibraryItem(db.Model):
    """PDFs, ebooks e materiais educativos para pacientes."""
    __tablename__ = "library_items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    cover_image = db.Column(db.String(255))
    category = db.Column(db.String(100), default="Geral")
    tags = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    is_public = db.Column(db.Boolean, default=True)
    download_count = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = db.relationship("User", foreign_keys=[uploaded_by])

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "filename": self.filename,
            "cover_image": self.cover_image,
            "category": self.category,
            "tags": self.tags,
            "download_count": self.download_count,
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(30), default="info")
    # info | success | warning | danger | appointment
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(255))
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "link": self.link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FinancialTransaction(db.Model):
    __tablename__ = "financial_transactions"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"))
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    professional_id = db.Column(db.Integer, db.ForeignKey("professionals.id"))
    type = db.Column(db.String(20), nullable=False)  # income | expense
    category = db.Column(db.String(100))
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    # dinheiro | cartao_credito | cartao_debito | pix | transferencia | convenio
    status = db.Column(db.String(20), default="pending")  # pending | paid | cancelled
    due_date = db.Column(db.Date)
    paid_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointment = db.relationship("Appointment", foreign_keys=[appointment_id])
    patient = db.relationship("User", foreign_keys=[patient_id])
    professional = db.relationship("Professional", foreign_keys=[professional_id])
    creator = db.relationship("User", foreign_keys=[created_by])

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "category": self.category,
            "description": self.description,
            "amount": self.amount,
            "payment_method": self.payment_method,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


class ContractionSession(db.Model):
    """Sessão do contador de contrações."""
    __tablename__ = "contraction_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    total_contractions = db.Column(db.Integer, default=0)
    avg_duration = db.Column(db.Float)   # seconds
    avg_interval = db.Column(db.Float)   # seconds
    sent_to_doctor = db.Column(db.Boolean, default=False)

    contractions = db.relationship("Contraction", backref="session", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "total_contractions": self.total_contractions,
            "avg_duration": self.avg_duration,
            "avg_interval": self.avg_interval,
        }


class Contraction(db.Model):
    __tablename__ = "contractions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("contraction_sessions.id"), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime)
    duration = db.Column(db.Float)   # seconds
    interval = db.Column(db.Float)   # seconds since last contraction
    intensity = db.Column(db.Integer)  # 1-10

    def to_dict(self):
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration": self.duration,
            "interval": self.interval,
            "intensity": self.intensity,
        }


class BirthPlan(db.Model):
    __tablename__ = "birth_plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    hospital = db.Column(db.String(200))
    doctor_name = db.Column(db.String(150))
    birth_type_preference = db.Column(db.String(50))  # normal | cesarea | sem_preferencia
    companion_name = db.Column(db.String(150))
    companion_relation = db.Column(db.String(100))
    pain_management = db.Column(db.Text)
    labor_preferences = db.Column(db.Text)
    delivery_preferences = db.Column(db.Text)
    postpartum_preferences = db.Column(db.Text)
    breastfeeding = db.Column(db.Boolean, default=True)
    skin_to_skin = db.Column(db.Boolean, default=True)
    cord_clamping = db.Column(db.String(50))  # immediate | delayed
    cord_blood_collection = db.Column(db.Boolean, default=False)
    photos_allowed = db.Column(db.Boolean, default=True)
    additional_notes = db.Column(db.Text)
    pdf_generated = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("birth_plan", uselist=False))


class SystemLog(db.Model):
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(100), nullable=False)
    entity = db.Column(db.String(50))  # user | appointment | document | etc
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    status = db.Column(db.String(20), default="success")  # success | error | warning
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "entity": self.entity,
            "entity_id": self.entity_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
