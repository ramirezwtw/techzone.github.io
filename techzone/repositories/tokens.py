"""Acceso a datos de los tokens de verificación y recuperación."""

import secrets
from datetime import timedelta
from typing import Optional

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from techzone.models import AuthToken, User, utcnow


def find(db: Session, token: str, purpose: str) -> Optional[AuthToken]:
    return db.scalars(
        select(AuthToken).where(AuthToken.token == token, AuthToken.purpose == purpose)
    ).first()


def issue(db: Session, user: User, purpose: str) -> AuthToken:
    """Emite un token nuevo e invalida los anteriores sin usar del mismo tipo."""
    db.execute(
        sql_delete(AuthToken).where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
    )

    instance = AuthToken(
        user_id=user.id,
        token=secrets.token_urlsafe(32),
        purpose=purpose,
        expires_at=utcnow() + timedelta(hours=AuthToken.TTL_HOURS[purpose]),
    )
    db.add(instance)
    db.commit()
    return instance
