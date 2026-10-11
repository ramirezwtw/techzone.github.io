"""Reglas de negocio de las solicitudes de armado de PC."""

from decimal import Decimal, InvalidOperation
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from techzone.models import BuildRequest, utcnow
from techzone.repositories import build_requests as requests_repo

# Vocabulario del formulario: lo consume la plantilla Jinja y también la API.
PURPOSE_OPTIONS = [
    "Gaming", "Trabajo", "Estudio", "Diseño gráfico", "Edición de video",
    "Programación", "Arquitectura", "Streaming", "Inteligencia artificial",
    "Uso general", "Otro",
]
GAME_OPTIONS = [
    "Fortnite", "GTA V", "GTA VI", "Valorant", "CS2", "Call of Duty",
    "Minecraft", "Apex Legends", "Warzone",
]
PROGRAM_OPTIONS = [
    "Adobe Photoshop", "Premiere Pro", "After Effects", "AutoCAD",
    "Blender", "Visual Studio Code", "Unreal Engine", "Unity",
]
PERIPHERAL_OPTIONS = [
    "Monitor", "Teclado", "Mouse", "Audífonos", "Micrófono", "Cámara web",
    "Parlantes", "Ninguno",
]
BUDGET_RANGES = [
    "Menos de $1.500.000",
    "$1.500.000 - $3.000.000",
    "$3.000.000 - $5.000.000",
    "$5.000.000 - $8.000.000",
    "Más de $8.000.000",
]
CUSTOM_BUDGET = "Otro (especificar)"
MIN_DESCRIPTION = 20

PENDING_STATUSES = ("Pendiente", "En revisión")
STATUS_WITH_RECOMMENDATION = "Recomendación lista"

RECOMMENDATION_FIELDS = (
    "rec_cpu", "rec_gpu", "rec_motherboard", "rec_ram", "rec_storage",
    "rec_psu", "rec_case", "rec_cooling", "rec_monitor", "rec_other",
)


def to_csv(values) -> str:
    return ",".join(v.strip() for v in values if v and v.strip())


def from_csv(value) -> list[str]:
    return [v for v in (value or "").split(",") if v]


# ──────────────────────────── consultas ────────────────────────────


def for_user(db: Session, user_id: int) -> Sequence[BuildRequest]:
    return requests_repo.list_by_user(db, user_id)


def all_requests(db: Session) -> Sequence[BuildRequest]:
    return requests_repo.list_all(db)


def get(db: Session, request_id: int) -> Optional[BuildRequest]:
    return requests_repo.get(db, request_id)


def belongs_to(build_request: BuildRequest, user_id: int) -> bool:
    return build_request.user_id == user_id


# ─────────────────────── creación desde el formulario ───────────────────────


def parse_form(form) -> tuple[dict, list[str]]:
    """Valida el formulario de armado y devuelve los campos listos para guardar."""
    purposes = form.getlist("purpose")
    purpose_other = form.get("purpose_other", "").strip()
    budget_range = form.get("budget_range", "").strip()
    budget_custom = form.get("budget_custom", "").strip()
    description = form.get("description", "").strip()
    has_components = form.get("has_components") == "si"
    pref_color = form.get("pref_color", "Me es indiferente")
    pref_color_other = form.get("pref_color_other", "").strip()

    errors = []
    if not purposes:
        errors.append("Selecciona para qué necesitas tu PC (al menos una opción).")
    if "Otro" in purposes and not purpose_other:
        errors.append("Especifica el uso en '¿Para qué necesitas tu PC?' → Otro.")

    budget = budget_custom if budget_range == CUSTOM_BUDGET else budget_range
    if not budget:
        errors.append("Indica tu presupuesto aproximado.")

    if len(description) < MIN_DESCRIPTION:
        errors.append(
            f"Cuéntanos con un poco más de detalle qué estás buscando "
            f"(mínimo {MIN_DESCRIPTION} caracteres)."
        )

    if pref_color == "Otro" and not pref_color_other:
        errors.append("Especifica el color preferido.")

    if errors:
        return {}, errors

    games_other = form.get("games_other", "").strip()
    programs_other = form.get("programs_other", "").strip()

    def current(field):
        # Los componentes actuales solo se guardan si el usuario dijo que los tiene.
        return form.get(field, "").strip() if has_components else ""

    data = dict(
        purpose=to_csv(purposes),
        purpose_other=purpose_other,
        budget=budget,
        games=to_csv(form.getlist("games") + ([games_other] if games_other else [])),
        programs=to_csv(
            form.getlist("programs") + ([programs_other] if programs_other else [])
        ),
        has_components=has_components,
        current_cpu=current("current_cpu"),
        current_gpu=current("current_gpu"),
        current_ram=current("current_ram"),
        current_storage=current("current_storage"),
        current_psu=current("current_psu"),
        current_motherboard=current("current_motherboard"),
        current_case=current("current_case"),
        current_monitor=current("current_monitor"),
        current_other=current("current_other"),
        pref_cpu_brand=form.get("pref_cpu_brand", "Sin preferencia"),
        pref_gpu_brand=form.get("pref_gpu_brand", "Sin preferencia"),
        pref_aesthetics=form.get("pref_aesthetics", "Me es indiferente"),
        pref_color=pref_color,
        pref_color_other=pref_color_other if pref_color == "Otro" else "",
        pref_size=form.get("pref_size", "Me es indiferente"),
        peripherals=to_csv(form.getlist("peripherals")),
        description=description,
        status="Pendiente",
    )
    return data, []


def create(db: Session, user_id: int, data: dict) -> BuildRequest:
    return requests_repo.create(db, dict(data, user_id=user_id))


def form_options() -> dict:
    return {
        "purpose_options": PURPOSE_OPTIONS,
        "game_options": GAME_OPTIONS,
        "program_options": PROGRAM_OPTIONS,
        "peripheral_options": PERIPHERAL_OPTIONS,
        "budget_ranges": BUDGET_RANGES,
    }


# ──────────────────────── gestión del administrador ─────────────────────────


def update_status(db: Session, build_request: BuildRequest, status: str) -> bool:
    if status not in BuildRequest.STATUSES:
        return False
    build_request.status = status
    requests_repo.save(db)
    return True


def save_recommendation(db: Session, build_request: BuildRequest, form) -> list[str]:
    """Guarda la recomendación del admin. Valida antes de tocar el objeto."""
    explanation = form.get("rec_explanation", "").strip()
    price_raw = form.get("rec_price_estimate", "").strip()

    errors = []
    price: Optional[Decimal] = None
    try:
        price = Decimal(price_raw) if price_raw else None
    except InvalidOperation:
        errors.append("El precio estimado debe ser un número válido.")

    if not explanation:
        errors.append("Agrega una explicación de la recomendación.")

    if errors:
        return errors

    for field in RECOMMENDATION_FIELDS:
        setattr(build_request, field, form.get(field, "").strip())
    build_request.rec_explanation = explanation
    build_request.rec_price_estimate = price
    build_request.rec_created_at = utcnow()

    # Al entregar la recomendación la solicitud avanza de estado sola.
    if build_request.status in PENDING_STATUSES:
        build_request.status = STATUS_WITH_RECOMMENDATION

    requests_repo.save(db)
    return []
