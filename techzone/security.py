"""Sesión, CSRF y control de acceso como dependencias de FastAPI.

Los decoradores `@login_required` / `@admin_required` de Flask se convierten en
dependencias (`Depends(require_login)` / `Depends(require_admin)`). Para poder
redirigir desde una dependencia se usa `RedirectException`, que `app.py`
traduce a una respuesta 303.
"""

import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from techzone.database import get_db
from techzone.models import User
from techzone.templating import CSRF_KEY, flash, url_for


class RedirectException(Exception):
    """Interrumpe el request y redirige (lo maneja el handler registrado en app.py)."""

    def __init__(self, url: str, status_code: int = 303):
        self.url = url
        self.status_code = status_code


def validate_csrf(request: Request, form_token: Optional[str]) -> bool:
    session_token = request.session.get(CSRF_KEY)
    return (
        bool(form_token)
        and bool(session_token)
        and secrets.compare_digest(form_token, session_token)
    )


def login_session(request: Request, user: User) -> None:
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["name"] = user.name
    request.session["role"] = user.role


def require_login(request: Request) -> int:
    """Devuelve el id del usuario en sesión; si no hay sesión, manda al login."""
    user_id = request.session.get("user_id")
    if not user_id:
        flash(request, "Debes iniciar sesión para continuar.", "error")
        raise RedirectException(url_for(request, "auth.login", next=request.url.path))
    return user_id


def require_admin(request: Request) -> int:
    user_id = require_login(request)
    if request.session.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para entrar al panel de administración.",
        )
    return user_id


def current_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """Usuario autenticado, o None si la sesión está vacía."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)
