import re
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from techzone.database import get_db
from techzone.mailer import send_password_reset_email, send_verification_email
from techzone.models import AuthToken, User
from techzone.security import login_session, validate_csrf
from techzone.templating import (
    back_or,
    external_url_for,
    flash,
    redirect,
    redirect_to,
    render,
)

router = APIRouter(default_response_class=HTMLResponse)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _issue_and_send_verification(request: Request, db: Session, user: User) -> None:
    token = AuthToken.issue(db, user, AuthToken.PURPOSE_VERIFY)
    db.commit()
    url = external_url_for(request, "auth.verify_email", token=token.token)
    send_verification_email(user, url)


def _safe_next(next_url: Optional[str]) -> Optional[str]:
    """Solo se acepta una ruta interna, para no convertir ?next= en un redirect abierto."""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return None


def _get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalars(select(User).where(User.email == email)).first()


@router.get("/login", name="auth.login")
def login_form(request: Request):
    return render(request, "login.html")


@router.post("/login", name="auth.login")
def login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(""),
    next_url: Optional[str] = Query(None, alias="next"),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "auth.login")

    email = email.strip().lower()

    user = _get_user_by_email(db, email)
    if user is None or not user.check_password(password):
        flash(request, "Correo o contraseña incorrectos.", "error")
        return render(request, "login.html", {"email": email}, status_code=401)

    if not user.active:
        flash(request, "Tu cuenta está desactivada. Contacta a un administrador.", "error")
        return render(request, "login.html", {"email": email}, status_code=403)

    login_session(request, user)
    flash(request, f"Bienvenido de nuevo, {user.name}.", "success")

    destination = _safe_next(next_url)
    if destination:
        return redirect_to(destination)
    if user.role == "admin":
        return redirect(request, "admin.dashboard")
    return redirect(request, "main.index")


@router.get("/registro", name="auth.registro")
def registro_form(request: Request):
    return render(request, "registro.html")


@router.post("/registro", name="auth.registro")
def registro(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "auth.registro")

    name = name.strip()
    email = email.strip().lower()

    errors = []
    if len(name) < 2:
        errors.append("Ingresa tu nombre completo.")
    if not EMAIL_RE.match(email):
        errors.append("Ingresa un correo electrónico válido.")
    if len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres.")
    if password != password_confirm:
        errors.append("Las contraseñas no coinciden.")
    if not errors and _get_user_by_email(db, email) is not None:
        errors.append("Ya existe una cuenta registrada con ese correo.")

    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request, "registro.html", {"name": name, "email": email}, status_code=400
        )

    user = User(name=name, email=email, role="user", active=True)
    user.set_password(password)
    db.add(user)
    db.flush()
    _issue_and_send_verification(request, db, user)

    login_session(request, user)
    flash(
        request,
        "Cuenta creada correctamente. Te enviamos un correo para verificar tu cuenta.",
        "success",
    )
    return redirect(request, "main.index")


@router.get("/logout", name="auth.logout")
def logout(request: Request):
    request.session.clear()
    flash(request, "Sesión cerrada correctamente.", "success")
    return redirect(request, "main.index")


@router.get("/verify-email/{token}", name="auth.verify_email")
def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    auth_token = AuthToken.find(db, token, AuthToken.PURPOSE_VERIFY)

    if auth_token is None or not auth_token.is_valid:
        flash(request, "El enlace de verificación no es válido o ya venció.", "error")
        return redirect(request, "auth.login")

    auth_token.user.email_verified = True
    auth_token.mark_used()
    db.commit()
    flash(request, "Tu cuenta quedó verificada correctamente.", "success")
    return redirect(request, "main.index")


@router.post("/reenviar-verificacion", name="auth.reenviar_verificacion")
def reenviar_verificacion(
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return back_or(request, "main.index")

    user = db.get(User, request.session.get("user_id")) if request.session.get("user_id") else None
    if user is None:
        flash(request, "Debes iniciar sesión para continuar.", "error")
        return redirect(request, "auth.login")

    if user.email_verified:
        flash(request, "Tu cuenta ya está verificada.", "success")
    else:
        _issue_and_send_verification(request, db, user)
        flash(request, "Te enviamos un nuevo correo de verificación.", "success")

    return back_or(request, "main.index")


@router.get("/olvide-contrasena", name="auth.forgot_password")
def forgot_password_form(request: Request):
    return render(request, "forgot_password.html")


@router.post("/olvide-contrasena", name="auth.forgot_password")
def forgot_password(
    request: Request,
    email: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "auth.forgot_password")

    user = _get_user_by_email(db, email.strip().lower())
    if user is not None and user.active:
        token = AuthToken.issue(db, user, AuthToken.PURPOSE_RESET)
        db.commit()
        url = external_url_for(request, "auth.reset_password", token=token.token)
        send_password_reset_email(user, url)

    # Mensaje genérico: no revela si el correo existe o no en el sistema.
    flash(
        request,
        "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.",
        "success",
    )
    return redirect(request, "auth.login")


@router.get("/restablecer-contrasena/{token}", name="auth.reset_password")
def reset_password_form(request: Request, token: str, db: Session = Depends(get_db)):
    auth_token = AuthToken.find(db, token, AuthToken.PURPOSE_RESET)
    if auth_token is None or not auth_token.is_valid:
        flash(request, "El enlace de recuperación no es válido o ya venció.", "error")
        return redirect(request, "auth.forgot_password")

    return render(request, "reset_password.html", {"token": token})


@router.post("/restablecer-contrasena/{token}", name="auth.reset_password")
def reset_password(
    request: Request,
    token: str,
    password: str = Form(""),
    password_confirm: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    auth_token = AuthToken.find(db, token, AuthToken.PURPOSE_RESET)

    if auth_token is None or not auth_token.is_valid:
        flash(request, "El enlace de recuperación no es válido o ya venció.", "error")
        return redirect(request, "auth.forgot_password")

    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "auth.reset_password", token=token)

    errors = []
    if len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres.")
    if password != password_confirm:
        errors.append("Las contraseñas no coinciden.")

    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(request, "reset_password.html", {"token": token}, status_code=400)

    auth_token.user.set_password(password)
    auth_token.mark_used()
    db.commit()
    flash(
        request,
        "Tu contraseña se actualizó correctamente. Ya puedes iniciar sesión.",
        "success",
    )
    return redirect(request, "auth.login")
