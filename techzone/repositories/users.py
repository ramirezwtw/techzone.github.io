"""Acceso a datos de usuarios."""

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from techzone.models import User


def get(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalars(select(User).where(User.email == email)).first()


def list_all(db: Session) -> Sequence[User]:
    return db.scalars(select(User).order_by(User.id.asc())).all()


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User)) or 0


def count_admins(db: Session) -> int:
    return (
        db.scalar(select(func.count()).select_from(User).where(User.role == "admin")) or 0
    )


def add(db: Session, user: User, commit: bool = True) -> User:
    db.add(user)
    if commit:
        db.commit()
    else:
        db.flush()
    return user


def save(db: Session) -> None:
    db.commit()
