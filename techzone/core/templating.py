"""Plantillas Jinja2 + utilidades que Flask daba "gratis" y en FastAPI hay que aportar.

Las plantillas de `templates/` se reutilizan tal cual, así que aquí se
reimplementan sobre Starlette las piezas de las que dependen:

* `url_for('blueprint.vista', ...)` → se resuelve por el *nombre* de la ruta
  de FastAPI (por eso cada ruta se registra con `name="auth.login"`, etc.).
* `csrf_token()`                    → token por sesión, igual que antes.
* `get_flashed_messages()`          → mensajes flash guardados en la cookie de sesión.
* `session`                         → el dict de `request.session`.
* `endpoint`                        → nombre de la ruta actual (lo usa el menú del admin).
"""

import os
import secrets
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

# La raíz del proyecto, un nivel arriba del paquete: ahí viven templates/,
# static/ y el database.db de desarrollo.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

FLASHES_KEY = "_flashes"
CSRF_KEY = "csrf_token"

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ──────────────────────────────── URLs ────────────────────────────────


def _find_route(app, name):
    """Ruta registrada con ese nombre; si hay varias (GET y POST), prefiere la GET."""
    matches = [route for route in app.routes if getattr(route, "name", None) == name]
    if not matches:
        return None
    for route in matches:
        if "GET" in (getattr(route, "methods", None) or set()):
            return route
    return matches[0]


def _relative_url_for(request: Request, name: str, **params) -> str:
    """Ruta (sin esquema ni host) de una vista, con los sobrantes como query string."""
    if name == "static":
        # En Flask era url_for('static', filename='css/style.css').
        filename = params.pop("filename", None) or params.pop("path", "")
        path = str(request.app.url_path_for("static", path=filename))
        return _with_query(path, params)

    route = _find_route(request.app, name)
    if route is None:
        raise RuntimeError(f"No existe ninguna ruta llamada '{name}'.")

    path_keys = set(getattr(route, "param_convertors", {}))
    path_params = {k: v for k, v in params.items() if k in path_keys}
    query = {k: v for k, v in params.items() if k not in path_keys}

    path = str(request.app.url_path_for(name, **path_params))
    return _with_query(path, query)


def _with_query(path: str, query) -> str:
    query = {k: v for k, v in query.items() if v is not None}
    if not query:
        return path
    return f"{path}?{urlencode(query)}"


def url_for(request: Request, name: str, **params) -> str:
    """Equivalente de Flask url_for(), respetando el root_path del servidor."""
    root_path = request.scope.get("root_path", "").rstrip("/")
    return root_path + _relative_url_for(request, name, **params)


def external_url_for(request: Request, name: str, **params) -> str:
    """Equivalente de Flask url_for(..., _external=True): sirve para los correos."""
    base = str(request.base_url).rstrip("/")
    return base + _relative_url_for(request, name, **params)


@pass_context
def _jinja_url_for(context, name: str, **params) -> str:
    return url_for(context["request"], name, **params)


# ──────────────────────────────── CSRF ────────────────────────────────


def generate_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_KEY)
    if not token:
        token = secrets.token_hex(32)
        request.session[CSRF_KEY] = token
    return token


@pass_context
def _jinja_csrf_token(context) -> str:
    return generate_csrf_token(context["request"])


# ──────────────────────── Mensajes flash ──────────────────────────────


def flash(request: Request, message: str, category: str = "success") -> None:
    request.session.setdefault(FLASHES_KEY, []).append([category, message])


def pop_flashes(request: Request, category_filter=()) -> list:
    """Saca los mensajes de la sesión: se muestran una sola vez.

    Lo usan la plantilla Jinja y también /api/v1/me, para que el frontend
    Astro pueda mostrar los mensajes de un redirect del backend.
    """
    messages = request.session.pop(FLASHES_KEY, [])
    if category_filter:
        messages = [m for m in messages if m[0] in category_filter]
    return messages


@pass_context
def _jinja_get_flashed_messages(context, with_categories: bool = False, category_filter=()):
    messages = pop_flashes(context["request"], category_filter)
    if with_categories:
        return [(category, message) for category, message in messages]
    return [message for _, message in messages]


# ────────────────────────── Render / redirect ─────────────────────────


def _endpoint_name(request: Request):
    route = request.scope.get("route")
    return getattr(route, "name", None)


def render(request: Request, template_name: str, context=None, status_code: int = 200):
    base_context = {
        "request": request,
        "session": request.session,
        "endpoint": _endpoint_name(request),
    }
    base_context.update(context or {})
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=base_context,
        status_code=status_code,
    )


def redirect(request: Request, name: str, status_code: int = 303, **params) -> RedirectResponse:
    """Redirección a una vista por nombre (303: el POST no se repite al recargar)."""
    return RedirectResponse(url_for(request, name, **params), status_code=status_code)


def redirect_to(url: str, status_code: int = 303) -> RedirectResponse:
    return RedirectResponse(url, status_code=status_code)


def back_or(request: Request, name: str, **params) -> RedirectResponse:
    """Equivalente de `request.referrer or url_for(...)`."""
    referer = request.headers.get("referer")
    if referer:
        return RedirectResponse(referer, status_code=303)
    return redirect(request, name, **params)


templates.env.globals["url_for"] = _jinja_url_for
templates.env.globals["csrf_token"] = _jinja_csrf_token
templates.env.globals["get_flashed_messages"] = _jinja_get_flashed_messages
templates.env.filters["split_csv"] = lambda value: [v for v in (value or "").split(",") if v]
