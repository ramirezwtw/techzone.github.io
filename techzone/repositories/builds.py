"""Acceso a datos de las builds recomendadas."""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from techzone.models import Build


def get(db: Session, build_id: int) -> Optional[Build]:
    return db.get(Build, build_id)


def get_active(db: Session, build_id: int) -> Optional[Build]:
    build = db.get(Build, build_id)
    return build if build is not None and build.active else None


def list_all(db: Session) -> Sequence[Build]:
    return db.scalars(select(Build).order_by(Build.id.asc())).all()


def list_active(db: Session) -> Sequence[Build]:
    return db.scalars(
        select(Build).where(Build.active.is_(True)).order_by(Build.id.asc())
    ).all()


def create(db: Session, data: dict) -> Build:
    build = Build(**data)
    db.add(build)
    db.commit()
    return build


def update(db: Session, build: Build, data: dict) -> Build:
    for key, value in data.items():
        setattr(build, key, value)
    db.commit()
    return build


def delete(db: Session, build: Build) -> None:
    db.delete(build)
    db.commit()
