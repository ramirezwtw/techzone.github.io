"""Reglas de negocio del catálogo: productos y builds recomendadas.

Aquí vive la validación de los formularios del panel y el orden en que se
guardan los cambios. Las consultas están en `techzone.repositories`.
"""

from decimal import Decimal, InvalidOperation
from typing import Sequence

from sqlalchemy.orm import Session

from techzone.models import Build, Product
from techzone.repositories import builds as builds_repo
from techzone.repositories import products as products_repo

DEFAULT_TIER_EMOJI = "🎮"


# ───────────────────────────── catálogo público ─────────────────────────────


def active_products(db: Session) -> Sequence[Product]:
    return products_repo.list_active(db)


def active_builds(db: Session) -> Sequence[Build]:
    return builds_repo.list_active(db)


def visible_build(db: Session, build_id: int):
    """Una build solo es visible en el sitio público si está activa."""
    return builds_repo.get_active(db, build_id)


# ──────────────────────────────── productos ─────────────────────────────────


def parse_product_form(form) -> tuple[dict, list[str]]:
    errors: list[str] = []
    name = form.get("name", "").strip()
    brand = form.get("brand", "").strip()
    description = form.get("description", "").strip()
    image_url = form.get("image_url", "").strip()

    if not name:
        errors.append("El nombre del producto es obligatorio.")
    if not brand:
        errors.append("La marca/categoría es obligatoria.")

    try:
        price = Decimal(form.get("price", "0") or "0")
        if price < 0:
            errors.append("El precio no puede ser negativo.")
    except InvalidOperation:
        errors.append("El precio debe ser un número válido.")
        price = Decimal("0")

    try:
        stock = int(form.get("stock", "0") or "0")
        if stock < 0:
            errors.append("El stock no puede ser negativo.")
    except ValueError:
        errors.append("El stock debe ser un número entero.")
        stock = 0

    data = dict(
        name=name,
        brand=brand,
        description=description,
        image_url=image_url,
        price=price,
        stock=stock,
        active=form.get("active") == "on",
    )
    return data, errors


def create_product(db: Session, data: dict) -> Product:
    return products_repo.create(db, data)


def update_product(db: Session, product: Product, data: dict) -> Product:
    return products_repo.update(db, product, data)


def toggle_product(db: Session, product: Product) -> bool:
    """Invierte la visibilidad y devuelve el estado nuevo."""
    products_repo.update(db, product, {"active": not product.active})
    return product.active


def delete_product(db: Session, product: Product) -> None:
    products_repo.delete(db, product)


# ───────────────────────────────── builds ───────────────────────────────────


def parse_build_form(form) -> tuple[dict, list[str]]:
    errors: list[str] = []
    tier = form.get("tier", "").strip()
    name = form.get("name", "").strip()
    tier_emoji = form.get("tier_emoji", DEFAULT_TIER_EMOJI).strip() or DEFAULT_TIER_EMOJI
    budget_label = form.get("budget_label", "").strip()

    if not tier:
        errors.append("El nivel (tier) es obligatorio.")
    if not name:
        errors.append("El nombre de la build es obligatorio.")
    if not budget_label:
        errors.append("Indica el rango de presupuesto.")

    try:
        # El porcentaje alimenta una barra de progreso: fuera de 0–100 no significa nada.
        performance_pct = int(form.get("performance_pct", "50") or "50")
        performance_pct = max(0, min(100, performance_pct))
    except ValueError:
        errors.append("El porcentaje de rendimiento debe ser un número entero.")
        performance_pct = 50

    data = dict(
        tier=tier,
        name=name,
        tier_emoji=tier_emoji,
        budget_label=budget_label,
        cpu=form.get("cpu", "").strip(),
        gpu=form.get("gpu", "").strip(),
        ram=form.get("ram", "").strip(),
        storage=form.get("storage", "").strip(),
        performance_note=form.get("performance_note", "").strip(),
        performance_pct=performance_pct,
        image_url=form.get("image_url", "").strip(),
        featured=form.get("featured") == "on",
        active=form.get("active") == "on",
    )
    return data, errors


def create_build(db: Session, data: dict) -> Build:
    return builds_repo.create(db, data)


def update_build(db: Session, build: Build, data: dict) -> Build:
    return builds_repo.update(db, build, data)


def toggle_build(db: Session, build: Build) -> bool:
    builds_repo.update(db, build, {"active": not build.active})
    return build.active


def delete_build(db: Session, build: Build) -> None:
    builds_repo.delete(db, build)
