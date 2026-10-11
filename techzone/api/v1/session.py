"""Sesión actual y token CSRF, para el frontend Astro.

Ojo con las cookies: tanto leer los flashes como pedir un token CSRF modifican
la sesión, así que la respuesta trae un Set-Cookie que el frontend debe
reenviar al navegador (lo hace `loadSession`/`loadCsrf` en frontend/src/lib).
"""

from fastapi import APIRouter, Request

from techzone.core.templating import generate_csrf_token, pop_flashes
from techzone.schemas.session import CsrfOut, FlashOut, SessionOut

router = APIRouter(tags=["sesión"])


@router.get("/me", response_model=SessionOut, summary="Quién está conectado")
def me(request: Request):
    """Sin cookie de sesión responde `authenticated: false`; nunca da error."""
    flashes = [
        FlashOut(category=category, message=message)
        for category, message in pop_flashes(request)
    ]

    user_id = request.session.get("user_id")
    if not user_id:
        return SessionOut(authenticated=False, flashes=flashes)

    role = request.session.get("role")
    return SessionOut(
        authenticated=True,
        name=request.session.get("name"),
        role=role,
        is_admin=role == "admin",
        flashes=flashes,
    )


@router.get("/csrf", response_model=CsrfOut, summary="Token CSRF del formulario")
def csrf(request: Request):
    """El mismo token que inyecta `csrf_token()` en las plantillas Jinja."""
    return CsrfOut(csrf_token=generate_csrf_token(request))
