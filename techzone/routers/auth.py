"""Registro, login, verificación de correo y recuperación de contraseña.

Capa HTTP: valida CSRF, delega en `services.accounts` y decide a dónde ir.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.core.security import login_session, validate_csrf
from techzone.core.templating import (
    back_or,
    external_url_for,
    flash,
    redirect,
    redirect_to,
    render,
)
from techzone.models import AuthToken
from techzone.repositories import users as users_repo
from techzone.services import accounts

router = APIRouter(default_response_class=HTMLResponse)


def _verification_url(request: Request):
    return lambda token: external_url_for(request, "auth.verify_email", token=token)


def _reset_url(request: Request):
    return lambda token: external_url_for(request, "auth.reset_password", token=token)


def _safe_next(next_url: Optional[str]) -> Optional[str]:
    """Solo se acepta una ruta interna, para no convertir ?next= en un redirect abierto."""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return None


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

    user, error = accounts.authenticate(db, email, password)
    email = accounts.normalize_email(email)

    if error == accounts.CREDENTIALS_INVALID:
        flash(request, "Correo o contraseña incorrectos.", "error")
        return render(request, "login.html", {"email": email}, status_code=401)

    if error == accounts.ACCOUNT_INACTIVE:
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

    user, errors = accounts.register(db, name, email, password, password_confirm)
    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request,
            "registro.html",
            {"name": name.strip(), "email": accounts.normalize_email(email)},
            status_code=400,
        )

    accounts.send_verification(db, user, _verification_url(request))

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
    auth_token = accounts.find_valid_token(db, token, AuthToken.PURPOSE_VERIFY)
    if auth_token is None:
        flash(request, "El enlace de verificación no es válido o ya venció.", "error")
        return redirect(request, "auth.login")

    accounts.confirm_email(db, auth_token)
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

    user_id = request.session.get("user_id")
    user = users_repo.get(db, user_id) if user_id else None
    if user is None:
        flash(request, "Debes iniciar sesión para continuar.", "error")
        return redirect(request, "auth.login")

    if user.email_verified:
        flash(request, "Tu cuenta ya está verificada.", "success")
    else:
        accounts.send_verification(db, user, _verification_url(request))
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

    accounts.start_password_reset(db, email, _reset_url(request))

    # Mensaje genérico: no revela si el correo existe o no en el sistema.
    flash(
        request,
        "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.",
        "success",
    )
    return redirect(request, "auth.login")


@router.get("/restablecer-contrasena/{token}", name="auth.reset_password")
def reset_password_form(request: Request, token: str, db: Session = Depends(get_db)):
    if accounts.find_valid_token(db, token, AuthToken.PURPOSE_RESET) is None:
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
    auth_token = accounts.find_valid_token(db, token, AuthToken.PURPOSE_RESET)
    if auth_token is None:
        flash(request, "El enlace de recuperación no es válido o ya venció.", "error")
        return redirect(request, "auth.forgot_password")

    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "auth.reset_password", token=token)

    errors = accounts.reset_password(db, auth_token, password, password_confirm)
    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(request, "reset_password.html", {"token": token}, status_code=400)

    flash(
        request,
        "Tu contraseña se actualizó correctamente. Ya puedes iniciar sesión.",
        "success",
    )
    return redirect(request, "auth.login")
