import os

from flask import Flask

from admin import admin_bp
from auth import auth_bp
from builds import builds_bp
from community import community_bp
from extensions import db, migrate
from main import main_bp
from profile import profile_bp
from security import generate_csrf_token
from seed_data import seed_admin_if_missing, seed_builds_if_empty, seed_products_if_empty

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Vercel inyecta esta variable de entorno automáticamente en toda Serverless
# Function (build, preview y producción). Nos sirve para detectar "estamos
# corriendo en Vercel" sin depender de si DATABASE_URL está o no definida.
ON_VERCEL = bool(os.environ.get("VERCEL"))


def _build_database_uri():
    """PostgreSQL obligatorio en Vercel vía DATABASE_URL; SQLite solo en desarrollo local."""
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

    return database_url


def _build_engine_options(database_uri):
    if database_uri.startswith("sqlite://"):
        return {}

    # Entorno serverless (Vercel): cada invocación puede ejecutarse en un
    # proceso/contenedor distinto, así que no conviene mantener un pool de
    # conexiones persistente. pool_pre_ping evita usar conexiones muertas y
    # un pool pequeño limita las conexiones simultáneas hacia Postgres.
    return {
        "pool_pre_ping": True,
        "pool_size": 1,
        "max_overflow": 2,
        "pool_recycle": 280,
    }


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    database_uri = _build_database_uri()
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = _build_engine_options(database_uri)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(builds_bp)

    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.jinja_env.filters["split_csv"] = lambda value: [v for v in (value or "").split(",") if v]

    # Sin consultas a la base de datos aquí: create_app() se ejecuta en cada
    # cold start de la Serverless Function de Vercel, y ahí no hay conexión
    # garantizada ni es el lugar para crear/inspeccionar tablas. El esquema
    # se gestiona con Alembic/Flask-Migrate (`flask db upgrade`) y los datos
    # iniciales con el comando `flask seed-db` (ver más abajo), ambos
    # ejecutados explícitamente por un humano, nunca en cada invocación.
    register_cli(app)

    return app


def register_cli(app):
    @app.cli.command("seed-db")
    def seed_db():
        """Crea el admin y los datos iniciales. Ejecutar a mano una vez por entorno."""
        with app.app_context():
            seed_products_if_empty()
            seed_builds_if_empty()
            seed_admin_if_missing(
                email=os.environ.get("ADMIN_EMAIL", "admin@techzone.app"),
                password=os.environ.get("ADMIN_PASSWORD", "TechZone2026!"),
            )
        print("Seed completado.")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
