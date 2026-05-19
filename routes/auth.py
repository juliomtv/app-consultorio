import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from database import db
from database.models import User, SystemLog

auth_bp = Blueprint("auth", __name__)


def log_action(action, user_id=None, details=None, status="success"):
    log = SystemLog(
        user_id=user_id,
        action=action,
        entity="user",
        entity_id=user_id,
        details=details,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:255],
        status=status,
    )
    db.session.add(log)
    db.session.commit()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            log_action("login_failed", details=f"Email: {email}", status="error")
            flash("E-mail ou senha incorretos.", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Sua conta está desativada. Entre em contato com a clínica.", "warning")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()
        log_action("login_success", user_id=user.id, details=f"Login de {user.name}")

        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)
        return _redirect_by_role(user)

    return render_template("auth/login.html")


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        cpf = request.form.get("cpf", "").strip()
        birth_date_str = request.form.get("birth_date", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not name or len(name) < 3:
            errors.append("Nome deve ter pelo menos 3 caracteres.")
        if not email:
            errors.append("E-mail é obrigatório.")
        if User.query.filter_by(email=email).first():
            errors.append("Este e-mail já está cadastrado.")
        if cpf and User.query.filter_by(cpf=cpf).first():
            errors.append("Este CPF já está cadastrado.")
        if len(password) < 8:
            errors.append("Senha deve ter pelo menos 8 caracteres.")
        if password != confirm_password:
            errors.append("As senhas não coincidem.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html")

        birth_date = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        user = User(
            name=name,
            email=email,
            phone=phone,
            cpf=cpf or None,
            birth_date=birth_date,
            role="patient",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_action("register", user_id=user.id, details=f"Novo paciente: {name}")

        flash("Cadastro realizado! Faça login para continuar.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        # Sempre mostra a mesma msg para não revelar se email existe
        flash("Se o e-mail existir, você receberá instruções de recuperação.", "info")

        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=2)
            db.session.commit()
            # Em produção: enviar e-mail com link de reset
            # send_reset_email(user, token)

    return render_template("auth/forgot_password.html")


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash("Link inválido ou expirado. Solicite novamente.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Senha deve ter pelo menos 8 caracteres.", "danger")
            return render_template("auth/reset_password.html", token=token)
        if password != confirm:
            flash("As senhas não coincidem.", "danger")
            return render_template("auth/reset_password.html", token=token)

        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash("Senha redefinida com sucesso! Faça login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/logout")
@login_required
def logout():
    log_action("logout", user_id=current_user.id)
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))


def _redirect_by_role(user):
    if user.is_admin():
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("patient.dashboard"))
