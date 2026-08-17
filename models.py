from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # 'user' | 'admin'
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    image_url = db.Column(db.String(500), nullable=False, default="")
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class BuildRequest(db.Model):
    """Solicitud de asesoría 'Ayúdame a armar mi PC' enviada por un usuario."""

    __tablename__ = "build_requests"

    STATUSES = ["Pendiente", "En revisión", "Recomendación lista", "Contactado", "Finalizado"]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # ── Uso y presupuesto ──────────────────────────────────
    purpose = db.Column(db.String(300), nullable=False, default="")  # CSV: Gaming,Trabajo,...
    purpose_other = db.Column(db.String(200), nullable=False, default="")
    budget = db.Column(db.String(120), nullable=False, default="")

    # ── Juegos / programas ─────────────────────────────────
    games = db.Column(db.Text, nullable=False, default="")
    programs = db.Column(db.Text, nullable=False, default="")

    # ── Componentes actuales ───────────────────────────────
    has_components = db.Column(db.Boolean, nullable=False, default=False)
    current_cpu = db.Column(db.String(150), nullable=False, default="")
    current_gpu = db.Column(db.String(150), nullable=False, default="")
    current_ram = db.Column(db.String(150), nullable=False, default="")
    current_storage = db.Column(db.String(150), nullable=False, default="")
    current_psu = db.Column(db.String(150), nullable=False, default="")
    current_motherboard = db.Column(db.String(150), nullable=False, default="")
    current_case = db.Column(db.String(150), nullable=False, default="")
    current_monitor = db.Column(db.String(150), nullable=False, default="")
    current_other = db.Column(db.String(200), nullable=False, default="")

    # ── Preferencias ────────────────────────────────────────
    pref_cpu_brand = db.Column(db.String(30), nullable=False, default="Sin preferencia")
    pref_gpu_brand = db.Column(db.String(30), nullable=False, default="Sin preferencia")
    pref_aesthetics = db.Column(db.String(30), nullable=False, default="Me es indiferente")
    pref_color = db.Column(db.String(30), nullable=False, default="Me es indiferente")
    pref_color_other = db.Column(db.String(60), nullable=False, default="")
    pref_size = db.Column(db.String(30), nullable=False, default="Me es indiferente")

    # ── Periféricos y descripción libre ────────────────────
    peripherals = db.Column(db.String(200), nullable=False, default="")  # CSV
    description = db.Column(db.Text, nullable=False, default="")

    status = db.Column(db.String(30), nullable=False, default="Pendiente")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # ── Recomendación del administrador ────────────────────
    rec_cpu = db.Column(db.String(150), nullable=False, default="")
    rec_gpu = db.Column(db.String(150), nullable=False, default="")
    rec_motherboard = db.Column(db.String(150), nullable=False, default="")
    rec_ram = db.Column(db.String(150), nullable=False, default="")
    rec_storage = db.Column(db.String(150), nullable=False, default="")
    rec_psu = db.Column(db.String(150), nullable=False, default="")
    rec_case = db.Column(db.String(150), nullable=False, default="")
    rec_cooling = db.Column(db.String(150), nullable=False, default="")
    rec_monitor = db.Column(db.String(150), nullable=False, default="")
    rec_other = db.Column(db.String(200), nullable=False, default="")
    rec_price_estimate = db.Column(db.Numeric(10, 2))
    rec_explanation = db.Column(db.Text, nullable=False, default="")
    rec_created_at = db.Column(db.DateTime)

    user = db.relationship("User", backref=db.backref("build_requests", lazy="dynamic"))

    @property
    def has_recommendation(self):
        return self.rec_created_at is not None


class Post(db.Model):
    """Publicación del foro de la Comunidad."""

    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    views = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("posts", lazy="dynamic"))

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def like_count(self):
        return self.likes.count()


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    post = db.relationship("Post", backref=db.backref("comments", lazy="dynamic"))
    user = db.relationship("User")


class PostLike(db.Model):
    __tablename__ = "post_likes"
    __table_args__ = (db.UniqueConstraint("post_id", "user_id", name="uq_post_user_like"),)

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    post = db.relationship("Post", backref=db.backref("likes", lazy="dynamic"))


class Build(db.Model):
    """Build de gaming destacada ('Gamer Inicial', 'Gamer Intermedio', ...)."""

    __tablename__ = "builds"

    id = db.Column(db.Integer, primary_key=True)
    tier = db.Column(db.String(60), nullable=False)  # Inicial | Intermedio | Profesional | ...
    name = db.Column(db.String(120), nullable=False)
    tier_emoji = db.Column(db.String(10), nullable=False, default="🎮")
    budget_label = db.Column(db.String(80), nullable=False, default="")
    cpu = db.Column(db.String(150), nullable=False, default="")
    gpu = db.Column(db.String(150), nullable=False, default="")
    ram = db.Column(db.String(150), nullable=False, default="")
    storage = db.Column(db.String(150), nullable=False, default="")
    performance_note = db.Column(db.String(200), nullable=False, default="")
    performance_pct = db.Column(db.Integer, nullable=False, default=50)
    image_url = db.Column(db.String(500), nullable=False, default="")
    featured = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
