"""Acceso a datos de las solicitudes de armado de PC."""

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from techzone.models import BuildRequest

PENDING_STATUSES = ["Pendiente", "En revisión"]


def get(db: Session, request_id: int) -> Optional[BuildRequest]:
    return db.get(BuildRequest, request_id)


def list_all(db: Session) -> Sequence[BuildRequest]:
    return db.scalars(
        select(BuildRequest)
        .options(selectinload(BuildRequest.user))
        .order_by(BuildRequest.created_at.desc())
    ).all()


def list_by_user(db: Session, user_id: int) -> Sequence[BuildRequest]:
    return db.scalars(
        select(BuildRequest)
        .where(BuildRequest.user_id == user_id)
        .order_by(BuildRequest.created_at.desc())
    ).all()


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(BuildRequest)) or 0


def count_pending(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(BuildRequest)
            .where(BuildRequest.status.in_(PENDING_STATUSES))
        )
        or 0
    )


def create(db: Session, data: dict) -> BuildRequest:
    build_request = BuildRequest(**data)
    db.add(build_request)
    db.commit()
    return build_request


def save(db: Session) -> None:
    db.commit()
