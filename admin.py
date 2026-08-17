from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import Build, BuildRequest, Product, User
from security import admin_required, validate_csrf

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def dashboard():
    total_users = User.query.count()
    total_products = Product.query.count()
    active_products = Product.query.filter_by(active=True).count()
    out_of_stock = Product.query.filter(Product.stock <= 0, Product.active.is_(True)).count()
    admins = User.query.filter_by(role="admin").count()
    pending_requests = BuildRequest.query.filter(BuildRequest.status.in_(["Pendiente", "En revisión"])).count()
    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_products=total_products,
        active_products=active_products,
        out_of_stock=out_of_stock,
        admins=admins,
        pending_requests=pending_requests,
    )


@admin_bp.route("/products")
@admin_required
def products():
    items = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/products.html", products=items)


def _parse_product_form(form):
    errors = []
    name = form.get("name", "").strip()
    brand = form.get("brand", "").strip()
    description = form.get("description", "").strip()
    image_url = form.get("image_url", "").strip()

    if not name:
        errors.append("El nombre del producto es obligatorio.")
    if not brand:
        errors.append("La marca/categoría es obligatoria.")

    try:
        price = Decimal(form.get("price", "0") or "0")
        if price < 0:
            errors.append("El precio no puede ser negativo.")
    except InvalidOperation:
        errors.append("El precio debe ser un número válido.")
        price = Decimal("0")

    try:
        stock = int(form.get("stock", "0") or "0")
        if stock < 0:
            errors.append("El stock no puede ser negativo.")
    except ValueError:
        errors.append("El stock debe ser un número entero.")
        stock = 0

    active = form.get("active") == "on"

    data = dict(
        name=name,
        brand=brand,
        description=description,
        image_url=image_url,
        price=price,
        stock=stock,
        active=active,
    )
    return data, errors


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("admin.product_new"))

        data, errors = _parse_product_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("admin/product_form.html", product=data, mode="new"), 400

        db.session.add(Product(**data))
        db.session.commit()
        flash("Producto creado correctamente.", "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=None, mode="new")


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("admin.product_edit", product_id=product_id))

        data, errors = _parse_product_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return (
                render_template(
                    "admin/product_form.html", product=data, mode="edit", product_id=product_id
                ),
                400,
            )

        for key, value in data.items():
            setattr(product, key, value)
        db.session.commit()
        flash("Cambios guardados. La página pública ya se actualizó.", "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=product, mode="edit", product_id=product_id)


@admin_bp.route("/products/<int:product_id>/toggle-active", methods=["POST"])
@admin_required
def product_toggle_active(product_id):
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(url_for("admin.products"))

    product = Product.query.get_or_404(product_id)
    product.active = not product.active
    db.session.commit()
    flash(f"{product.name} {'activado' if product.active else 'desactivado'}.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(url_for("admin.products"))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Producto eliminado permanentemente.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/users")
@admin_required
def users():
    items = User.query.order_by(User.id.asc()).all()
    return render_template("admin/users.html", users=items)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def user_toggle_active(user_id):
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(url_for("admin.users"))

    user = User.query.get_or_404(user_id)
    if user.id == session.get("user_id"):
        flash("No puedes desactivar tu propia cuenta.", "error")
        return redirect(url_for("admin.users"))

    user.active = not user.active
    db.session.commit()
    flash(f"{user.name} {'activado' if user.active else 'desactivado'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def user_change_role(user_id):
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(url_for("admin.users"))

    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    if new_role not in ("user", "admin"):
        flash("Rol inválido.", "error")
        return redirect(url_for("admin.users"))

    if user.id == session.get("user_id") and new_role != "admin":
        flash("No puedes quitarte el rol de administrador a ti mismo.", "error")
        return redirect(url_for("admin.users"))

    user.role = new_role
    db.session.commit()
    flash(f"Rol de {user.name} actualizado a {new_role}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/solicitudes")
@admin_required
def solicitudes():
    items = BuildRequest.query.order_by(BuildRequest.created_at.desc()).all()
    return render_template("admin/solicitudes.html", requests=items)


@admin_bp.route("/solicitudes/<int:request_id>", methods=["GET", "POST"])
@admin_required
def solicitud_detalle(request_id):
    build_request = BuildRequest.query.get_or_404(request_id)
    products = Product.query.filter_by(active=True).order_by(Product.name.asc()).all()

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("admin.solicitud_detalle", request_id=request_id))

        action = request.form.get("action")

        if action == "update_status":
            new_status = request.form.get("status")
            if new_status not in BuildRequest.STATUSES:
                flash("Estado inválido.", "error")
            else:
                build_request.status = new_status
                db.session.commit()
                flash("Estado de la solicitud actualizado.", "success")
            return redirect(url_for("admin.solicitud_detalle", request_id=request_id))

        if action == "save_recommendation":
            form = request.form
            build_request.rec_cpu = form.get("rec_cpu", "").strip()
            build_request.rec_gpu = form.get("rec_gpu", "").strip()
            build_request.rec_motherboard = form.get("rec_motherboard", "").strip()
            build_request.rec_ram = form.get("rec_ram", "").strip()
            build_request.rec_storage = form.get("rec_storage", "").strip()
            build_request.rec_psu = form.get("rec_psu", "").strip()
            build_request.rec_case = form.get("rec_case", "").strip()
            build_request.rec_cooling = form.get("rec_cooling", "").strip()
            build_request.rec_monitor = form.get("rec_monitor", "").strip()
            build_request.rec_other = form.get("rec_other", "").strip()
            build_request.rec_explanation = form.get("rec_explanation", "").strip()

            price_raw = form.get("rec_price_estimate", "").strip()
            try:
                build_request.rec_price_estimate = Decimal(price_raw) if price_raw else None
            except InvalidOperation:
                flash("El precio estimado debe ser un número válido.", "error")
                return redirect(url_for("admin.solicitud_detalle", request_id=request_id))

            if not build_request.rec_explanation:
                flash("Agrega una explicación de la recomendación.", "error")
                return redirect(url_for("admin.solicitud_detalle", request_id=request_id))

            build_request.rec_created_at = datetime.utcnow()
            if build_request.status in ("Pendiente", "En revisión"):
                build_request.status = "Recomendación lista"
            db.session.commit()
            flash("Recomendación guardada. El usuario ya puede verla en su perfil.", "success")
            return redirect(url_for("admin.solicitud_detalle", request_id=request_id))

    return render_template("admin/solicitud_detalle.html", r=build_request, products=products)


@admin_bp.route("/builds")
@admin_required
def builds():
    items = Build.query.order_by(Build.id.asc()).all()
    return render_template("admin/builds.html", builds=items)


def _parse_build_form(form):
    errors = []
    tier = form.get("tier", "").strip()
    name = form.get("name", "").strip()
    tier_emoji = form.get("tier_emoji", "🎮").strip() or "🎮"
    budget_label = form.get("budget_label", "").strip()
    cpu = form.get("cpu", "").strip()
    gpu = form.get("gpu", "").strip()
    ram = form.get("ram", "").strip()
    storage = form.get("storage", "").strip()
    performance_note = form.get("performance_note", "").strip()
    image_url = form.get("image_url", "").strip()

    if not tier:
        errors.append("El nivel (tier) es obligatorio.")
    if not name:
        errors.append("El nombre de la build es obligatorio.")
    if not budget_label:
        errors.append("Indica el rango de presupuesto.")

    try:
        performance_pct = int(form.get("performance_pct", "50") or "50")
        performance_pct = max(0, min(100, performance_pct))
    except ValueError:
        errors.append("El porcentaje de rendimiento debe ser un número entero.")
        performance_pct = 50

    data = dict(
        tier=tier,
        name=name,
        tier_emoji=tier_emoji,
        budget_label=budget_label,
        cpu=cpu,
        gpu=gpu,
        ram=ram,
        storage=storage,
        performance_note=performance_note,
        performance_pct=performance_pct,
        image_url=image_url,
        featured=form.get("featured") == "on",
        active=form.get("active") == "on",
    )
    return data, errors


@admin_bp.route("/builds/new", methods=["GET", "POST"])
@admin_required
def build_new():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("admin.build_new"))

        data, errors = _parse_build_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("admin/build_form.html", build=data, mode="new"), 400

        db.session.add(Build(**data))
        db.session.commit()
        flash("Build creada correctamente.", "success")
        return redirect(url_for("admin.builds"))

    return render_template("admin/build_form.html", build=None, mode="new")


@admin_bp.route("/builds/<int:build_id>/edit", methods=["GET", "POST"])
@admin_required
def build_edit(build_id):
    build = Build.query.get_or_404(build_id)

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("admin.build_edit", build_id=build_id))

        data, errors = _parse_build_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("admin/build_form.html", build=data, mode="edit", build_id=build_id), 400

        for key, value in data.items():
            setattr(build, key, value)
        db.session.commit()
        flash("Cambios guardados. La página pública ya se actualizó.", "success")
        return redirect(url_for("admin.builds"))

    return render_template("admin/build_form.html", build=build, mode="edit", build_id=build_id)


@admin_bp.route("/builds/<int:build_id>/toggle-active", methods=["POST"])
@admin_required
def build_toggle_active(build_id):
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(url_for("admin.builds"))

    build = Build.query.get_or_404(build_id)
    build.active = not build.active
    db.session.commit()
    flash(f"{build.name} {'activada' if build.active else 'desactivada'}.", "success")
    return redirect(url_for("admin.builds"))


@admin_bp.route("/builds/<int:build_id>/delete", methods=["POST"])
@admin_required
def build_delete(build_id):
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(url_for("admin.builds"))

    build = Build.query.get_or_404(build_id)
    db.session.delete(build)
    db.session.commit()
    flash("Build eliminada permanentemente.", "success")
    return redirect(url_for("admin.builds"))
