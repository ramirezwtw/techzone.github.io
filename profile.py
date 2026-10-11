from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import BuildRequest, User
from security import require_login, validate_csrf
from templating import flash, redirect, render

router = APIRouter(prefix="/perfil", default_response_class=HTMLResponse)

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
PERIPHERAL_OPTIONS = ["Monitor", "Teclado", "Mouse", "Audífonos", "Micrófono", "Cámara web", "Parlantes", "Ninguno"]
BUDGET_RANGES = [
    "Menos de $1.500.000",
    "$1.500.000 - $3.000.000",
    "$3.000.000 - $5.000.000",
    "$5.000.000 - $8.000.000",
    "Más de $8.000.000",
]


def _csv(values):
    return ",".join(v.strip() for v in values if v and v.strip())


def _from_csv(value):
    return [v for v in (value or "").split(",") if v]


def _options_context(form, selected_purposes, selected_games, selected_programs, selected_peripherals):
    return {
        "purpose_options": PURPOSE_OPTIONS,
        "game_options": GAME_OPTIONS,
        "program_options": PROGRAM_OPTIONS,
        "peripheral_options": PERIPHERAL_OPTIONS,
        "budget_ranges": BUDGET_RANGES,
        "form": form,
        "selected_purposes": selected_purposes,
        "selected_games": selected_games,
        "selected_programs": selected_programs,
        "selected_peripherals": selected_peripherals,
    }


@router.get("/", name="profile.index")
def index(
    request: Request,
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
        )
    requests_ = db.scalars(
        select(BuildRequest)
        .where(BuildRequest.user_id == user.id)
        .order_by(BuildRequest.created_at.desc())
    ).all()
    return render(request, "profile/index.html", {"user": user, "requests": requests_})


@router.get("/solicitudes/{request_id}", name="profile.solicitud_detalle")
def solicitud_detalle(
    request: Request,
    request_id: int,
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    build_request = db.get(BuildRequest, request_id)
    if build_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada."
        )
    if build_request.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Esta solicitud no es tuya."
        )
    return render(request, "profile/solicitud_detalle.html", {"r": build_request})


@router.get("/armar-pc", name="profile.armar_pc")
def armar_pc_form(
    request: Request,
    purpose: str = "",
    budget: str = "",
    build: str = "",
    user_id: int = Depends(require_login),
):
    # Precarga opcional desde una build (?purpose=Gaming&budget=...&build=...)
    prefill_form = {}
    selected_purposes = []
    if purpose.strip():
        selected_purposes = [purpose.strip()]
    if budget.strip():
        prefill_form["budget_range"] = "Otro (especificar)"
        prefill_form["budget_custom"] = budget.strip()
    if build.strip():
        prefill_form["description"] = f"Me interesa la build recomendada '{build.strip()}'. "

    return render(
        request,
        "profile/armar_pc.html",
        _options_context(prefill_form, selected_purposes, [], [], []),
    )


@router.post("/armar-pc", name="profile.armar_pc")
async def armar_pc(
    request: Request,
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    # El formulario tiene varios campos de selección múltiple (purpose, games,
    # programs, peripherals), así que se lee completo y se usa getlist().
    form = await request.form()

    if not validate_csrf(request, form.get("csrf_token")):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "profile.armar_pc")

    purposes = form.getlist("purpose")
    purpose_other = form.get("purpose_other", "").strip()
    budget_range = form.get("budget_range", "").strip()
    budget_custom = form.get("budget_custom", "").strip()
    description = form.get("description", "").strip()
    has_components = form.get("has_components") == "si"

    errors = []
    if not purposes:
        errors.append("Selecciona para qué necesitas tu PC (al menos una opción).")
    if "Otro" in purposes and not purpose_other:
        errors.append("Especifica el uso en '¿Para qué necesitas tu PC?' → Otro.")

    budget = budget_custom if budget_range == "Otro (especificar)" else budget_range
    if not budget:
        errors.append("Indica tu presupuesto aproximado.")

    if len(description) < 20:
        errors.append("Cuéntanos con un poco más de detalle qué estás buscando (mínimo 20 caracteres).")

    pref_color = form.get("pref_color", "Me es indiferente")
    pref_color_other = form.get("pref_color_other", "").strip()
    if pref_color == "Otro" and not pref_color_other:
        errors.append("Especifica el color preferido.")

    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request,
            "profile/armar_pc.html",
            _options_context(
                form,
                purposes,
                form.getlist("games"),
                form.getlist("programs"),
                form.getlist("peripherals"),
            ),
            status_code=400,
        )

    games_other = form.get("games_other", "").strip()
    programs_other = form.get("programs_other", "").strip()

    build_request = BuildRequest(
        user_id=user_id,
        purpose=_csv(purposes),
        purpose_other=purpose_other,
        budget=budget,
        games=_csv(form.getlist("games") + ([games_other] if games_other else [])),
        programs=_csv(form.getlist("programs") + ([programs_other] if programs_other else [])),
        has_components=has_components,
        current_cpu=form.get("current_cpu", "").strip() if has_components else "",
        current_gpu=form.get("current_gpu", "").strip() if has_components else "",
        current_ram=form.get("current_ram", "").strip() if has_components else "",
        current_storage=form.get("current_storage", "").strip() if has_components else "",
        current_psu=form.get("current_psu", "").strip() if has_components else "",
        current_motherboard=form.get("current_motherboard", "").strip() if has_components else "",
        current_case=form.get("current_case", "").strip() if has_components else "",
        current_monitor=form.get("current_monitor", "").strip() if has_components else "",
        current_other=form.get("current_other", "").strip() if has_components else "",
        pref_cpu_brand=form.get("pref_cpu_brand", "Sin preferencia"),
        pref_gpu_brand=form.get("pref_gpu_brand", "Sin preferencia"),
        pref_aesthetics=form.get("pref_aesthetics", "Me es indiferente"),
        pref_color=pref_color,
        pref_color_other=pref_color_other if pref_color == "Otro" else "",
        pref_size=form.get("pref_size", "Me es indiferente"),
        peripherals=_csv(form.getlist("peripherals")),
        description=description,
        status="Pendiente",
    )
    db.add(build_request)
    db.commit()

    flash(
        request,
        "Tu solicitud fue enviada. Nuestro equipo la revisará y te recomendará una configuración.",
        "success",
    )
    return redirect(request, "profile.index")
