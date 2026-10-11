"""TechZone — aplicación FastAPI (server-side rendering con plantillas Jinja2).

La instancia se expone en `app.py` (raíz), que es el entrypoint que usan
tanto `uvicorn app:app --reload` como @vercel/python (ver vercel.json).
"""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from techzone.api import v1 as api_v1
from techzone.core.database import ON_VERCEL
from techzone.core.security import RedirectException
from techzone.routers import admin, auth, builds, community, main, profile

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# El frontend Astro se sirve desde el mismo dominio, así que en producción no
# hace falta CORS. En desarrollo vive en su propio puerto (4321) y sí lo pide;
# son endpoints públicos de solo lectura, sin cookies (allow_credentials=False).
DEV_ORIGINS = ["http://localhost:4321", "http://127.0.0.1:4321"]
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", ",".join([] if ON_VERCEL else DEV_ORIGINS)).split(",")
    if origin.strip()
]

ERROR_TITLES = {
    403: "No tienes acceso a esta página",
    404: "Página no encontrada",
}


def create_app() -> FastAPI:
    app = FastAPI(title="TechZone", description="Asesoría y catálogo de hardware para PC.")

    # Sesión firmada en cookie, equivalente a la sesión de Flask.
    # max_age=None → cookie de sesión del navegador (sin fecha de expiración),
    # igual que antes y como dice la política de cookies del sitio.
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        session_cookie="techzone_session",
        max_age=None,
        same_site="lax",
        https_only=ON_VERCEL,
    )

    if CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=CORS_ORIGINS,
            allow_methods=["GET"],
            allow_headers=["*"],
            allow_credentials=False,
        )

    app.mount(
        "/static",
        StaticFiles(directory=os.path.join(BASE_DIR, "static")),
        name="static",
    )

    # API JSON (la consume el frontend Astro) + sitio renderizado con Jinja.
    app.include_router(api_v1.router)
    app.include_router(main.router)
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(profile.router)
    app.include_router(community.router)
    app.include_router(builds.router)

    register_exception_handlers(app)

    # Sin consultas a la base de datos durante el arranque: este módulo se
    # importa en cada cold start de la Serverless Function de Vercel, y ahí no
    # hay conexión garantizada ni es el lugar para crear/inspeccionar tablas.
    # El esquema se gestiona con Alembic (`alembic upgrade head`) y los datos
    # iniciales con `python seed.py`, ambos ejecutados a mano por un humano.
    return app


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RedirectException)
    async def handle_redirect(request: Request, exc: RedirectException):
        """Permite que una dependencia (p. ej. require_login) redirija al login."""
        return RedirectResponse(exc.url, status_code=exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else ""

        # La API responde JSON; el sitio renderizado, una página de error.
        if request.url.path.startswith(f"{api_v1.router.prefix}/") or request.url.path.startswith(
            "/api/"
        ):
            return JSONResponse(
                {"detail": detail or "Error"},
                status_code=exc.status_code,
                headers=getattr(exc, "headers", None),
            )

        title = ERROR_TITLES.get(exc.status_code, "Algo salió mal")
        return HTMLResponse(
            f"""<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{exc.status_code} · TechZone</title>
    <link rel="stylesheet" href="/static/css/style.css" />
  </head>
  <body style="display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center">
    <main style="padding:2rem">
      <h1>{exc.status_code} — {title}</h1>
      <p>{detail}</p>
      <p><a href="/">Volver al inicio</a></p>
    </main>
  </body>
</html>""",
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )


app = create_app()
