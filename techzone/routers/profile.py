"""Perfil del usuario y formulario 'Ayúdame a armar mi PC'."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.core.security import require_login, validate_csrf
from techzone.core.templating import flash, redirect, render
from techzone.repositories import users as users_repo
from techzone.services import build_requests as requests_service

router = APIRouter(prefix="/perfil", default_response_class=HTMLResponse)


def _form_context(form, selected_purposes, selected_games, selected_programs, selected_peripherals):
    """Opciones del formulario + lo que el usuario ya había elegido."""
    return dict(
        requests_service.form_options(),
        form=form,
        selected_purposes=selected_purposes,
        selected_games=selected_games,
        selected_programs=selected_programs,
        selected_peripherals=selected_peripherals,
    )


@router.get("/", name="profile.index")
def index(
    request: Request,
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    user = users_repo.get(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
        )
    return render(
        request,
        "profile/index.html",
        {"user": user, "requests": requests_service.for_user(db, user.id)},
    )


@router.get("/solicitudes/{request_id}", name="profile.solicitud_detalle")
def solicitud_detalle(
    request: Request,
    request_id: int,
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    build_request = requests_service.get(db, request_id)
    if build_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada."
        )
    if not requests_service.belongs_to(build_request, user_id):
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
    prefill = {}
    selected_purposes = []
    if purpose.strip():
        selected_purposes = [purpose.strip()]
    if budget.strip():
        prefill["budget_range"] = requests_service.CUSTOM_BUDGET
        prefill["budget_custom"] = budget.strip()
    if build.strip():
        prefill["description"] = f"Me interesa la build recomendada '{build.strip()}'. "

    return render(
        request,
        "profile/armar_pc.html",
        _form_context(prefill, selected_purposes, [], [], []),
    )


@router.post("/armar-pc", name="profile.armar_pc")
async def armar_pc(
    request: Request,
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    # El formulario tiene varios campos de selección múltiple (purpose, games,
    # programs, peripherals), así que se lee completo y el servicio usa getlist().
    form = await request.form()

    if not validate_csrf(request, form.get("csrf_token")):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "profile.armar_pc")

    data, errors = requests_service.parse_form(form)
    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request,
            "profile/armar_pc.html",
            _form_context(
                form,
                form.getlist("purpose"),
                form.getlist("games"),
                form.getlist("programs"),
                form.getlist("peripherals"),
            ),
            status_code=400,
        )

    requests_service.create(db, user_id, data)
    flash(
        request,
        "Tu solicitud fue enviada. Nuestro equipo la revisará y te recomendará una configuración.",
        "success",
    )
    return redirect(request, "profile.index")
