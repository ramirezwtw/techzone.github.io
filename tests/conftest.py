"""Configuración común de las pruebas.

Importante: la URL de la base de datos se fija ANTES de importar `database`
o `app`, porque `database.py` construye el engine al importarse. Cada prueba
corre contra un SQLite temporal que se recrea desde cero.
"""

import os
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

_TEST_DB = Path(tempfile.mkdtemp(prefix="techzone-tests-")) / "test.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.as_posix()
os.environ["SECRET_KEY"] = "clave-de-pruebas"
os.environ.pop("VERCEL", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import User  # noqa: E402
from seed_data import (  # noqa: E402
    seed_admin_if_missing,
    seed_builds_if_empty,
    seed_products_if_empty,
)

ADMIN_EMAIL = "admin@techzone.app"
ADMIN_PASSWORD = "TechZone2026!"
USER_NAME = "Ana Pérez"
USER_EMAIL = "ana@example.com"
USER_PASSWORD = "secreta123"


@pytest.fixture
def reset_db():
    """Esquema limpio + datos iniciales (9 productos, 3 builds, 1 admin)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_products_if_empty(session)
        seed_builds_if_empty(session)
        seed_admin_if_missing(session, email=ADMIN_EMAIL, password=ADMIN_PASSWORD)
    return None


@pytest.fixture
def db(reset_db):
    """Fábrica de sesiones: `with db() as s:` abre una sesión nueva y actualizada."""
    return SessionLocal


@pytest.fixture
def client(reset_db):
    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client


@pytest.fixture
def admin_client(client):
    from helpers import login

    response = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert response.status_code == 303, "el login del admin debería redirigir"
    return client


@pytest.fixture
def user_client(client):
    from helpers import create_user, login

    create_user()
    response = login(client, USER_EMAIL, USER_PASSWORD)
    assert response.status_code == 303, "el login del usuario debería redirigir"
    return client


@pytest.fixture
def other_user_id():
    """Un segundo usuario, para probar accesos cruzados."""
    from helpers import create_user

    return create_user(email="otro@example.com", name="Otro Usuario")
