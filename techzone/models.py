"""Modelos SQLAlchemy 2.0 (estilo declarativo tipado).

El esquema es exactamente el mismo que tenía la versión Flask-SQLAlchemy:
mismos nombres de tabla y de columna, así que la base de datos existente
(PostgreSQL o el SQLite local) sigue sirviendo sin migraciones nuevas.
"""

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    delete,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from techzone.database import Base


def utcnow():
    """UTC sin tzinfo: las columnas son DateTime naive, como en la versión Flask."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # 'user' | 'admin'
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    build_requests: Mapped[list["BuildRequest"]] = relationship(
        back_populates="user", order_by="BuildRequest.created_at.desc()"
    )
    posts: Mapped[list["Post"]] = relationship(back_populates="user")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class AuthToken(Base):
    """Token de un solo uso para verificación de correo o recuperación de contraseña."""

    __tablename__ = "auth_tokens"

    PURPOSE_VERIFY = "verify"
    PURPOSE_RESET = "reset"
    TTL_HOURS = {PURPOSE_VERIFY: 24, PURPOSE_RESET: 1}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    user: Mapped["User"] = relationship()

    @classmethod
    def issue(cls, db: Session, user: "User", purpose: str) -> "AuthToken":
        # Invalida cualquier token anterior sin usar del mismo tipo para este usuario.
        db.execute(
            delete(cls).where(
                cls.user_id == user.id,
                cls.purpose == purpose,
                cls.used_at.is_(None),
            )
        )

        instance = cls(
            user_id=user.id,
            token=secrets.token_urlsafe(32),
            purpose=purpose,
            expires_at=utcnow() + timedelta(hours=cls.TTL_HOURS[purpose]),
        )
        db.add(instance)
        return instance

    @classmethod
    def find(cls, db: Session, token: str, purpose: str) -> Optional["AuthToken"]:
        return db.scalars(select(cls).where(cls.token == token, cls.purpose == purpose)).first()

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > utcnow()

    def mark_used(self) -> None:
        self.used_at = utcnow()


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    brand: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class BuildRequest(Base):
    """Solicitud de asesoría 'Ayúdame a armar mi PC' enviada por un usuario."""

    __tablename__ = "build_requests"

    STATUSES = ["Pendiente", "En revisión", "Recomendación lista", "Contactado", "Finalizado"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # ── Uso y presupuesto ──────────────────────────────────
    purpose: Mapped[str] = mapped_column(String(300), nullable=False, default="")  # CSV: Gaming,Trabajo
    purpose_other: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    budget: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # ── Juegos / programas ─────────────────────────────────
    games: Mapped[str] = mapped_column(Text, nullable=False, default="")
    programs: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── Componentes actuales ───────────────────────────────
    has_components: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_cpu: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    current_gpu: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    current_ram: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    current_storage: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    current_psu: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    current_motherboard: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    current_case: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    current_monitor: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    current_other: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    # ── Preferencias ────────────────────────────────────────
    pref_cpu_brand: Mapped[str] = mapped_column(String(30), nullable=False, default="Sin preferencia")
    pref_gpu_brand: Mapped[str] = mapped_column(String(30), nullable=False, default="Sin preferencia")
    pref_aesthetics: Mapped[str] = mapped_column(String(30), nullable=False, default="Me es indiferente")
    pref_color: Mapped[str] = mapped_column(String(30), nullable=False, default="Me es indiferente")
    pref_color_other: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    pref_size: Mapped[str] = mapped_column(String(30), nullable=False, default="Me es indiferente")

    # ── Periféricos y descripción libre ────────────────────
    peripherals: Mapped[str] = mapped_column(String(200), nullable=False, default="")  # CSV
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Pendiente")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    # ── Recomendación del administrador ────────────────────
    rec_cpu: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_gpu: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_motherboard: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_ram: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_storage: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_psu: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_case: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_cooling: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_monitor: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    rec_other: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    rec_price_estimate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    rec_explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rec_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="build_requests")

    @property
    def has_recommendation(self) -> bool:
        return self.rec_created_at is not None


class Post(Base):
    """Publicación del foro de la Comunidad."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="post",
        order_by="Comment.created_at.asc()",
        cascade="all, delete-orphan",
    )
    likes: Mapped[list["PostLike"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )

    @property
    def comment_count(self) -> int:
        return len(self.comments)

    @property
    def like_count(self) -> int:
        return len(self.likes)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    post: Mapped["Post"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship()


class PostLike(Base):
    __tablename__ = "post_likes"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_post_user_like"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    post: Mapped["Post"] = relationship(back_populates="likes")


class Build(Base):
    """Build de gaming destacada ('Gamer Inicial', 'Gamer Intermedio', ...)."""

    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tier: Mapped[str] = mapped_column(String(60), nullable=False)  # Inicial | Intermedio | ...
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tier_emoji: Mapped[str] = mapped_column(String(10), nullable=False, default="🎮")
    budget_label: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    cpu: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    gpu: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    ram: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    storage: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    performance_note: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    performance_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
