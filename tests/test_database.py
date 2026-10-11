"""Construcción de la URL de conexión y opciones del engine.

Es la parte que decide cómo se conecta la app a PostgreSQL (Neon, Supabase,
Vercel Postgres...) y cuándo cae al SQLite local.
"""

import pytest
from sqlalchemy.pool import NullPool

from techzone import database

NEON_URL = (
    "postgresql://usuario:clave@ep-cool-name-123456-pooler.us-east-2.aws.neon.tech/techzone"
)


def test_sin_database_url_usa_sqlite_local(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(database, "ON_VERCEL", False)

    url = database.build_database_url()
    assert url.startswith("sqlite:///")
    assert url.endswith("database.db")


def test_sin_database_url_en_vercel_falla_con_mensaje_claro(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(database, "ON_VERCEL", True)

    with pytest.raises(RuntimeError, match="DATABASE_URL es obligatoria en Vercel"):
        database.build_database_url()


def test_normaliza_el_esquema_y_el_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", NEON_URL.replace("postgresql://", "postgres://"))
    url = database.build_database_url()
    assert url.startswith("postgresql+psycopg2://")


def test_postgres_remoto_exige_tls(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", NEON_URL)
    url = database.build_database_url()
    assert "sslmode=require" in url


def test_no_pisa_el_sslmode_que_ya_viene(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", NEON_URL + "?sslmode=verify-full")
    url = database.build_database_url()
    assert "sslmode=verify-full" in url
    assert "sslmode=require" not in url


def test_conserva_los_demas_parametros(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", NEON_URL + "?channel_binding=require")
    url = database.build_database_url()
    assert "channel_binding=require" in url
    assert "sslmode=require" in url


def test_postgres_local_no_exige_tls(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/techzone")
    url = database.build_database_url()
    assert "sslmode" not in url


def test_opciones_del_engine_en_sqlite():
    options = database.build_engine_options("sqlite:///database.db")
    assert options["connect_args"] == {"check_same_thread": False}


def test_opciones_del_engine_en_vercel(monkeypatch):
    monkeypatch.setattr(database, "ON_VERCEL", True)
    options = database.build_engine_options("postgresql+psycopg2://u:p@host/db")
    # En serverless no se mantiene un pool propio: una conexión por request.
    assert options["poolclass"] is NullPool
    assert options["pool_pre_ping"] is True


def test_opciones_del_engine_fuera_de_vercel(monkeypatch):
    monkeypatch.setattr(database, "ON_VERCEL", False)
    options = database.build_engine_options("postgresql+psycopg2://u:p@host/db")
    assert options["pool_pre_ping"] is True
    assert "poolclass" not in options
