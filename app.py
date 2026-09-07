import os

from flask import Flask
from sqlalchemy import inspect, text

from admin import admin_bp
from auth import auth_bp
from builds import builds_bp
from community import community_bp
from extensions import db
from main import main_bp
from profile import profile_bp
from security import generate_csrf_token
from seed_data import seed_admin_if_missing, seed_builds_if_empty, seed_products_if_empty

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _migrate_schema():
    """Agrega columnas nuevas a tablas existentes (sqlite no soporta migraciones automáticas)."""
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "email_verified" not in columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0"))
        db.session.execute(text("UPDATE users SET email_verified = 1 WHERE role = 'admin'"))
        db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(builds_bp)

    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.jinja_env.filters["split_csv"] = lambda value: [v for v in (value or "").split(",") if v]

    with app.app_context():
        db.create_all()
        _migrate_schema()
        seed_products_if_empty()
        seed_builds_if_empty()
        seed_admin_if_missing(
            email=os.environ.get("ADMIN_EMAIL", "admin@techzone.app"),
            password=os.environ.get("ADMIN_PASSWORD", "TechZone2026!"),
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
