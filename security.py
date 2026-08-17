import functools
import secrets

from flask import abort, flash, redirect, request, session, url_for


def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf(form_token):
    session_token = session.get("csrf_token")
    return bool(form_token) and bool(session_token) and secrets.compare_digest(form_token, session_token)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para continuar.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para continuar.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped
