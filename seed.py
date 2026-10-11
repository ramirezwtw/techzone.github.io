"""Datos iniciales de TechZone (reemplaza al comando `flask seed-db`).

Uso:
    python seed.py                   # crea catálogo, builds y el usuario admin
    python seed.py --create-tables   # además crea las tablas (útil en local con SQLite)

El esquema en producción se gestiona con Alembic:  alembic upgrade head
"""

import argparse
import os

from database import Base, DATABASE_URL, SessionLocal, engine
from seed_data import seed_admin_if_missing, seed_builds_if_empty, seed_products_if_empty


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga los datos iniciales de TechZone.")
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="Crea las tablas que falten antes de insertar los datos.",
    )
    args = parser.parse_args()

    print(f"Base de datos: {DATABASE_URL.split('@')[-1]}")

    if args.create_tables:
        Base.metadata.create_all(bind=engine)
        print("Tablas creadas/verificadas.")

    with SessionLocal() as db:
        seed_products_if_empty(db)
        seed_builds_if_empty(db)
        seed_admin_if_missing(
            db,
            email=os.environ.get("ADMIN_EMAIL", "admin@techzone.app"),
            password=os.environ.get("ADMIN_PASSWORD", "TechZone2026!"),
        )

    print("Seed completado.")


if __name__ == "__main__":
    main()
