"""Reglas de negocio de las cuentas: registro, autenticación y tokens de correo."""

import re
from typing import Optional

from sqlalchemy.orm import Session

from techzone.core.mailer import send_password_reset_email, send_verification_email
from techzone.models import AuthToken, User
from techzone.repositories import tokens as tokens_repo
from techzone.repositories import users as users_repo

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8

# Motivos por los que se rechaza un login (el router decide el status HTTP).
CREDENTIALS_INVALID = "credentials"
ACCOUNT_INACTIVE = "inactive"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_passwords(password: str, password_confirm: str) -> list[str]:
    errors = []
    if len(password) < MIN_PASSWORD:
        errors.append(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.")
    if password != password_confirm:
        errors.append("Las contraseñas no coinciden.")
    return errors


def authenticate(db: Session, email: str, password: str) -> tuple[Optional[User], Optional[str]]:
    user = users_repo.get_by_email(db, normalize_email(email))
    if user is None or not user.check_password(password):
        return None, CREDENTIALS_INVALID
    if not user.active:
        return user, ACCOUNT_INACTIVE
    return user, None


def register(
    db: Session, name: str, email: str, password: str, password_confirm: str
) -> tuple[Optional[User], list[str]]:
    """Crea la cuenta si los datos son válidos. No inicia sesión: eso es del router."""
    name = (name or "").strip()
    email = normalize_email(email)

    errors = []
    if len(name) < 2:
        errors.append("Ingresa tu nombre completo.")
    if not EMAIL_RE.match(email):
        errors.append("Ingresa un correo electrónico válido.")
    errors.extend(validate_passwords(password, password_confirm))
    if not errors and users_repo.get_by_email(db, email) is not None:
        errors.append("Ya existe una cuenta registrada con ese correo.")

    if errors:
        return None, errors

    user = User(name=name, email=email, role="user", active=True)
    user.set_password(password)
    users_repo.add(db, user, commit=False)
    return user, []


# ──────────────────────── tokens de correo ────────────────────────


def find_valid_token(db: Session, token: str, purpose: str) -> Optional[AuthToken]:
    auth_token = tokens_repo.find(db, token, purpose)
    if auth_token is None or not auth_token.is_valid:
        return None
    return auth_token


def send_verification(db: Session, user: User, url_builder) -> None:
    """Emite el token y envía el correo. `url_builder(token)` arma el enlace absoluto."""
    auth_token = tokens_repo.issue(db, user, AuthToken.PURPOSE_VERIFY)
    send_verification_email(user, url_builder(auth_token.token))


def confirm_email(db: Session, auth_token: AuthToken) -> None:
    auth_token.user.email_verified = True
    auth_token.mark_used()
    users_repo.save(db)


def start_password_reset(db: Session, email: str, url_builder) -> None:
    """Si el correo existe y está activo, envía el enlace. Nunca revela si existe."""
    user = users_repo.get_by_email(db, normalize_email(email))
    if user is None or not user.active:
        return

    auth_token = tokens_repo.issue(db, user, AuthToken.PURPOSE_RESET)
    send_password_reset_email(user, url_builder(auth_token.token))


def reset_password(
    db: Session, auth_token: AuthToken, password: str, password_confirm: str
) -> list[str]:
    errors = validate_passwords(password, password_confirm)
    if errors:
        return errors

    auth_token.user.set_password(password)
    auth_token.mark_used()
    users_repo.save(db)
    return []


# ──────────────────────── administración de usuarios ────────────────────────


def toggle_active(db: Session, user: User) -> bool:
    user.active = not user.active
    users_repo.save(db)
    return user.active


def change_role(db: Session, user: User, role: str) -> None:
    user.role = role
    users_repo.save(db)
