import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import User
from security import validate_csrf

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
        db.session.commit()

        session.clear()
        session["user_id"] = user.id
        session["name"] = user.name
        session["role"] = user.role
        flash("Cuenta creada correctamente. ¡Bienvenido a TechZone!", "success")
        return redirect(url_for("main.index"))

    return render_template("registro.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("main.index"))
