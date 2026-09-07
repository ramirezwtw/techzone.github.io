import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from extensions import db
from mailer import send_password_reset_email, send_verification_email
from models import AuthToken, User
from security import validate_csrf

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _issue_and_send_verification(user):
    token = AuthToken.issue(user, AuthToken.PURPOSE_VERIFY)
    db.session.commit()
    url = url_for("auth.verify_email", token=token.token, _external=True)
    send_verification_email(user, url)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("auth.login"))

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash("Correo o contraseña incorrectos.", "error")
            return render_template("login.html", email=email), 401

        if not user.active:
            flash("Tu cuenta está desactivada. Contacta a un administrador.", "error")
            return render_template("login.html", email=email), 403

        session.clear()
        session["user_id"] = user.id
        session["name"] = user.name
        session["role"] = user.role
        flash(f"Bienvenido de nuevo, {user.name}.", "success")

        next_url = request.args.get("next")
        if user.role == "admin":
            return redirect(next_url or url_for("admin.dashboard"))
        return redirect(next_url or url_for("main.index"))

    return render_template("login.html")


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("auth.registro"))

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        errors = []
        if len(name) < 2:
            errors.append("Ingresa tu nombre completo.")
        if not EMAIL_RE.match(email):
            errors.append("Ingresa un correo electrónico válido.")
        if len(password) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")
        if password != password_confirm:
            errors.append("Las contraseñas no coinciden.")
        if not errors and User.query.filter_by(email=email).first() is not None:
            errors.append("Ya existe una cuenta registrada con ese correo.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("registro.html", name=name, email=email), 400

        user = User(name=name, email=email, role="user", active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        _issue_and_send_verification(user)

        session.clear()
        session["user_id"] = user.id
        session["name"] = user.name
        session["role"] = user.role
        flash("Cuenta creada correctamente. Te enviamos un correo para verificar tu cuenta.", "success")
        return redirect(url_for("main.index"))

    return render_template("registro.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    auth_token = AuthToken.query.filter_by(token=token, purpose=AuthToken.PURPOSE_VERIFY).first()

    if auth_token is None or not auth_token.is_valid:
        flash("El enlace de verificación no es válido o ya venció.", "error")
        return redirect(url_for("auth.login"))

    auth_token.user.email_verified = True
    auth_token.mark_used()
    db.session.commit()
    flash("Tu cuenta quedó verificada correctamente.", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/reenviar-verificacion", methods=["POST"])
def reenviar_verificacion():
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request.referrer or url_for("main.index"))

    user = User.query.get(session.get("user_id"))
    if user is None:
        flash("Debes iniciar sesión para continuar.", "error")
        return redirect(url_for("auth.login"))

    if user.email_verified:
        flash("Tu cuenta ya está verificada.", "success")
    else:
        _issue_and_send_verification(user)
        flash("Te enviamos un nuevo correo de verificación.", "success")

    return redirect(request.referrer or url_for("main.index"))


@auth_bp.route("/olvide-contrasena", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("auth.forgot_password"))

        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is not None and user.active:
            token = AuthToken.issue(user, AuthToken.PURPOSE_RESET)
            db.session.commit()
            url = url_for("auth.reset_password", token=token.token, _external=True)
            send_password_reset_email(user, url)

        # Mensaje genérico: no revela si el correo existe o no en el sistema.
        flash("Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.", "success")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth_bp.route("/restablecer-contrasena/<token>", methods=["GET", "POST"])
def reset_password(token):
    auth_token = AuthToken.query.filter_by(token=token, purpose=AuthToken.PURPOSE_RESET).first()

    if auth_token is None or not auth_token.is_valid:
        flash("El enlace de recuperación no es válido o ya venció.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("auth.reset_password", token=token))

        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        errors = []
        if len(password) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")
        if password != password_confirm:
            errors.append("Las contraseñas no coinciden.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("reset_password.html", token=token), 400

        auth_token.user.set_password(password)
        auth_token.mark_used()
        db.session.commit()
        flash("Tu contraseña se actualizó correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)
