import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
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

        if user.role == "patient":
            flash("O portal do paciente não está disponível. Entre em contato com a clínica.", "warning")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()
        # Grava o tenant do usuário na sessão para resolução correta em dev (localhost)
        if user.tenant_id:
            session['tenant_id'] = user.tenant_id
        log_action("login_success", user_id=user.id, details=f"Login de {user.name}")

        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)
        return _redirect_by_role(user)

    return render_template("auth/login.html")


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
    session.pop('tenant_id', None)
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))


def _redirect_by_role(user):
    return redirect(url_for("admin.dashboard"))
