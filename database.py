"""Capa de base de datos (SQLAlchemy 2.0) para la app FastAPI.

En producción (Vercel) PostgreSQL es obligatorio vía DATABASE_URL: ahí entra
la cadena de conexión del proveedor que se esté usando — Neon, Supabase,
Railway, Render, Vercel Postgres... El código no depende de ninguno en
particular, solo de que DATABASE_URL apunte a un PostgreSQL accesible.

En local, si no hay DATABASE_URL, se usa el SQLite de siempre (database.db)
para poder desarrollar sin conexión a internet.
"""

import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Vercel inyecta esta variable de entorno automáticamente en toda Serverless
# Function (build, preview y producción). Nos sirve para detectar "estamos
# corriendo en Vercel" sin depender de si DATABASE_URL está o no definida.
ON_VERCEL = bool(os.environ.get("VERCEL"))

_LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}


def build_database_url():
    """PostgreSQL obligatorio en Vercel vía DATABASE_URL; SQLite solo en local."""
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        if ON_VERCEL:
            # No hay filesystem persistente en Vercel: abrir un archivo SQLite
            # ahí falla con "unable to open database file". En vez de dejar
            # que ese error confuso ocurra más adelante, fallamos aquí mismo
            # con un mensaje claro de qué falta configurar.
            raise RuntimeError(
                "DATABASE_URL es obligatoria en Vercel: configúrala como variable de entorno "
                "de PostgreSQL en el proyecto de Vercel (Production/Preview) y vuelve a desplegar."
            )
        return "sqlite:///" + os.path.join(BASE_DIR, "database.db")

    # Algunos proveedores (Heroku, Render, ...) entregan "postgres://", pero
    # SQLAlchemy 1.4+ requiere el esquema "postgresql://". Forzamos además el
    # driver psycopg2, que es el que se instala en requirements.txt.
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://"):]
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg2://" + database_url[len("postgresql://"):]

    return _ensure_sslmode(database_url)


def _ensure_sslmode(database_url):
    """Fuerza TLS en PostgreSQL remoto (Neon y compañía lo exigen)."""
    parts = urlparse(database_url)
    if not parts.scheme.startswith("postgresql"):
        return database_url

    host = (parts.hostname or "").lower()
    if host in _LOCAL_HOSTS:
        return database_url

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if "sslmode" not in query:
        query["sslmode"] = "require"
        parts = parts._replace(query=urlencode(query))

    return urlunparse(parts)


def build_engine_options(database_url):
    if database_url.startswith("sqlite"):
        # SQLite + servidor ASGI: las conexiones pueden viajar entre hilos
        # del threadpool de Starlette, así que hay que relajar esa validación.
        return {"connect_args": {"check_same_thread": False}}

    if ON_VERCEL:
        # Entorno serverless: cada invocación puede ejecutarse en un
        # proceso/contenedor distinto, así que mantener un pool propio solo
        # acumula conexiones muertas contra PostgreSQL. NullPool abre y cierra
        # la conexión por request; si el proveedor ofrece un endpoint con
        # pooler (p. ej. el host "-pooler" de Neon), conviene apuntar
        # DATABASE_URL a ese host.
        return {"poolclass": NullPool, "pool_pre_ping": True}

    return {"pool_pre_ping": True, "pool_recycle": 280}


DATABASE_URL = build_database_url()

engine = create_engine(DATABASE_URL, **build_engine_options(DATABASE_URL))

# expire_on_commit=False: las plantillas Jinja siguen leyendo atributos de los
# objetos después del commit, y así no se dispara un SELECT extra por atributo.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependencia de FastAPI: una sesión de BD por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
