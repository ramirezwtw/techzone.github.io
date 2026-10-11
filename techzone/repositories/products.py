"""Acceso a datos de productos. Ninguna regla de negocio vive aquí."""

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from techzone.models import Product


def get(db: Session, product_id: int) -> Optional[Product]:
    return db.get(Product, product_id)


def list_all(db: Session) -> Sequence[Product]:
    return db.scalars(select(Product).order_by(Product.id.desc())).all()


def list_active(db: Session) -> Sequence[Product]:
    return db.scalars(
        select(Product).where(Product.active.is_(True)).order_by(Product.id.asc())
    ).all()


def list_active_by_name(db: Session) -> Sequence[Product]:
    return db.scalars(
        select(Product).where(Product.active.is_(True)).order_by(Product.name.asc())
    ).all()


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Product)) or 0


def count_active(db: Session) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(Product).where(Product.active.is_(True))
        )
        or 0
    )


def count_out_of_stock(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.stock <= 0, Product.active.is_(True))
        )
        or 0
    )


def create(db: Session, data: dict) -> Product:
    product = Product(**data)
    db.add(product)
    db.commit()
    return product


def update(db: Session, product: Product, data: dict) -> Product:
    for key, value in data.items():
        setattr(product, key, value)
    db.commit()
    return product


def delete(db: Session, product: Product) -> None:
    db.delete(product)
    db.commit()
