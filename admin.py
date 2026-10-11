from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import Build, BuildRequest, Product, User, utcnow
from security import require_admin, validate_csrf
from templating import flash, redirect, render

# El control de acceso se aplica a todo el router: equivale al @admin_required
# que llevaba cada vista en la versión Flask.
router = APIRouter(
    prefix="/admin",
    default_response_class=HTMLResponse,
    dependencies=[Depends(require_admin)],
)


def _count(db: Session, model, *criteria) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return db.scalar(statement) or 0


def _get_or_404(db: Session, model, pk: int, message: str):
    instance = db.get(model, pk)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    return instance


# ──────────────────────────── Dashboard ───────────────────────────────


@router.get("/", name="admin.dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "admin/dashboard.html",
        {
            "total_users": _count(db, User),
            "total_products": _count(db, Product),
            "active_products": _count(db, Product, Product.active.is_(True)),
            "out_of_stock": _count(db, Product, Product.stock <= 0, Product.active.is_(True)),
            "admins": _count(db, User, User.role == "admin"),
            "pending_requests": _count(
                db, BuildRequest, BuildRequest.status.in_(["Pendiente", "En revisión"])
            ),
        },
    )


# ──────────────────────────── Productos ───────────────────────────────


@router.get("/products", name="admin.products")
def products(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(Product).order_by(Product.id.desc())).all()
    return render(request, "admin/products.html", {"products": items})


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

    data = dict(
        name=name,
        brand=brand,
        description=description,
        image_url=image_url,
        price=price,
        stock=stock,
        active=form.get("active") == "on",
    )
    return data, errors


def _product_form_payload(
    name: str,
    brand: str,
    description: str,
    image_url: str,
    price: str,
    stock: str,
    active: Optional[str],
):
    return {
        "name": name,
        "brand": brand,
        "description": description,
        "image_url": image_url,
        "price": price,
        "stock": stock,
        "active": active,
    }


@router.get("/products/new", name="admin.product_new")
def product_new_form(request: Request):
    return render(request, "admin/product_form.html", {"product": None, "mode": "new"})


@router.post("/products/new", name="admin.product_new")
def product_new(
    request: Request,
    name: str = Form(""),
    brand: str = Form(""),
    description: str = Form(""),
    image_url: str = Form(""),
    price: str = Form("0"),
    stock: str = Form("0"),
    active: Optional[str] = Form(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.product_new")

    data, errors = _parse_product_form(
        _product_form_payload(name, brand, description, image_url, price, stock, active)
    )
    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request,
            "admin/product_form.html",
            {"product": data, "mode": "new"},
            status_code=400,
        )

    db.add(Product(**data))
    db.commit()
    flash(request, "Producto creado correctamente.", "success")
    return redirect(request, "admin.products")


@router.get("/products/{product_id}/edit", name="admin.product_edit")
def product_edit_form(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = _get_or_404(db, Product, product_id, "Producto no encontrado.")
    return render(
        request,
        "admin/product_form.html",
        {"product": product, "mode": "edit", "product_id": product_id},
    )


@router.post("/products/{product_id}/edit", name="admin.product_edit")
def product_edit(
    request: Request,
    product_id: int,
    name: str = Form(""),
    brand: str = Form(""),
    description: str = Form(""),
    image_url: str = Form(""),
    price: str = Form("0"),
    stock: str = Form("0"),
    active: Optional[str] = Form(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    product = _get_or_404(db, Product, product_id, "Producto no encontrado.")

    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.product_edit", product_id=product_id)

    data, errors = _parse_product_form(
        _product_form_payload(name, brand, description, image_url, price, stock, active)
    )
    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request,
            "admin/product_form.html",
            {"product": data, "mode": "edit", "product_id": product_id},
            status_code=400,
        )

    for key, value in data.items():
        setattr(product, key, value)
    db.commit()
    flash(request, "Cambios guardados. La página pública ya se actualizó.", "success")
    return redirect(request, "admin.products")


@router.post("/products/{product_id}/toggle-active", name="admin.product_toggle_active")
def product_toggle_active(
    request: Request,
    product_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.products")

    product = _get_or_404(db, Product, product_id, "Producto no encontrado.")
    product.active = not product.active
    db.commit()
    flash(request, f"{product.name} {'activado' if product.active else 'desactivado'}.", "success")
    return redirect(request, "admin.products")


@router.post("/products/{product_id}/delete", name="admin.product_delete")
def product_delete(
    request: Request,
    product_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.products")

    product = _get_or_404(db, Product, product_id, "Producto no encontrado.")
    db.delete(product)
    db.commit()
    flash(request, "Producto eliminado permanentemente.", "success")
    return redirect(request, "admin.products")


# ───────────────────────────── Usuarios ───────────────────────────────


@router.get("/users", name="admin.users")
def users(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(User).order_by(User.id.asc())).all()
    return render(request, "admin/users.html", {"users": items})


@router.post("/users/{user_id}/toggle-active", name="admin.user_toggle_active")
def user_toggle_active(
    request: Request,
    user_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.users")

    user = _get_or_404(db, User, user_id, "Usuario no encontrado.")
    if user.id == request.session.get("user_id"):
        flash(request, "No puedes desactivar tu propia cuenta.", "error")
        return redirect(request, "admin.users")

    user.active = not user.active
    db.commit()
    flash(request, f"{user.name} {'activado' if user.active else 'desactivado'}.", "success")
    return redirect(request, "admin.users")


@router.post("/users/{user_id}/role", name="admin.user_change_role")
def user_change_role(
    request: Request,
    user_id: int,
    role: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.users")

    user = _get_or_404(db, User, user_id, "Usuario no encontrado.")
    if role not in ("user", "admin"):
        flash(request, "Rol inválido.", "error")
        return redirect(request, "admin.users")

    if user.id == request.session.get("user_id") and role != "admin":
        flash(request, "No puedes quitarte el rol de administrador a ti mismo.", "error")
        return redirect(request, "admin.users")

    user.role = role
    db.commit()
    flash(request, f"Rol de {user.name} actualizado a {role}.", "success")
    return redirect(request, "admin.users")


# ──────────────────────────── Solicitudes ─────────────────────────────


@router.get("/solicitudes", name="admin.solicitudes")
def solicitudes(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(
        select(BuildRequest)
        .options(selectinload(BuildRequest.user))
        .order_by(BuildRequest.created_at.desc())
    ).all()
    return render(request, "admin/solicitudes.html", {"requests": items})


def _render_solicitud(request: Request, db: Session, build_request: BuildRequest):
    products = db.scalars(
        select(Product).where(Product.active.is_(True)).order_by(Product.name.asc())
    ).all()
    return render(
        request,
        "admin/solicitud_detalle.html",
        {"r": build_request, "products": products},
    )


@router.get("/solicitudes/{request_id}", name="admin.solicitud_detalle")
def solicitud_detalle_form(request: Request, request_id: int, db: Session = Depends(get_db)):
    build_request = _get_or_404(db, BuildRequest, request_id, "Solicitud no encontrada.")
    return _render_solicitud(request, db, build_request)


@router.post("/solicitudes/{request_id}", name="admin.solicitud_detalle")
async def solicitud_detalle(request: Request, request_id: int, db: Session = Depends(get_db)):
    build_request = _get_or_404(db, BuildRequest, request_id, "Solicitud no encontrada.")

    # Un solo formulario con dos acciones (cambiar estado / guardar
    # recomendación) y muchos campos: se lee completo, como en la versión Flask.
    form = await request.form()

    if not validate_csrf(request, form.get("csrf_token")):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.solicitud_detalle", request_id=request_id)

    action = form.get("action")

    if action == "update_status":
        new_status = form.get("status")
        if new_status not in BuildRequest.STATUSES:
            flash(request, "Estado inválido.", "error")
        else:
            build_request.status = new_status
            db.commit()
            flash(request, "Estado de la solicitud actualizado.", "success")
        return redirect(request, "admin.solicitud_detalle", request_id=request_id)

    if action == "save_recommendation":
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
            db.rollback()
            flash(request, "El precio estimado debe ser un número válido.", "error")
            return redirect(request, "admin.solicitud_detalle", request_id=request_id)

        if not build_request.rec_explanation:
            db.rollback()
            flash(request, "Agrega una explicación de la recomendación.", "error")
            return redirect(request, "admin.solicitud_detalle", request_id=request_id)

        build_request.rec_created_at = utcnow()
        if build_request.status in ("Pendiente", "En revisión"):
            build_request.status = "Recomendación lista"
        db.commit()
        flash(
            request,
            "Recomendación guardada. El usuario ya puede verla en su perfil.",
            "success",
        )
        return redirect(request, "admin.solicitud_detalle", request_id=request_id)

    return _render_solicitud(request, db, build_request)


# ────────────────────────────── Builds ────────────────────────────────


@router.get("/builds", name="admin.builds")
def builds(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(Build).order_by(Build.id.asc())).all()
    return render(request, "admin/builds.html", {"builds": items})


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


def _build_form_payload(
    tier: str,
    name: str,
    tier_emoji: str,
    budget_label: str,
    cpu: str,
    gpu: str,
    ram: str,
    storage: str,
    performance_note: str,
    performance_pct: str,
    image_url: str,
    featured: Optional[str],
    active: Optional[str],
):
    return {
        "tier": tier,
        "name": name,
        "tier_emoji": tier_emoji,
        "budget_label": budget_label,
        "cpu": cpu,
        "gpu": gpu,
        "ram": ram,
        "storage": storage,
        "performance_note": performance_note,
        "performance_pct": performance_pct,
        "image_url": image_url,
        "featured": featured,
        "active": active,
    }


@router.get("/builds/new", name="admin.build_new")
def build_new_form(request: Request):
    return render(request, "admin/build_form.html", {"build": None, "mode": "new"})


@router.post("/builds/new", name="admin.build_new")
def build_new(
    request: Request,
    tier: str = Form(""),
    name: str = Form(""),
    tier_emoji: str = Form("🎮"),
    budget_label: str = Form(""),
    cpu: str = Form(""),
    gpu: str = Form(""),
    ram: str = Form(""),
    storage: str = Form(""),
    performance_note: str = Form(""),
    performance_pct: str = Form("50"),
    image_url: str = Form(""),
    featured: Optional[str] = Form(None),
    active: Optional[str] = Form(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.build_new")

    data, errors = _parse_build_form(
        _build_form_payload(
            tier, name, tier_emoji, budget_label, cpu, gpu, ram, storage,
            performance_note, performance_pct, image_url, featured, active,
        )
    )
    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request, "admin/build_form.html", {"build": data, "mode": "new"}, status_code=400
        )

    db.add(Build(**data))
    db.commit()
    flash(request, "Build creada correctamente.", "success")
    return redirect(request, "admin.builds")


@router.get("/builds/{build_id}/edit", name="admin.build_edit")
def build_edit_form(request: Request, build_id: int, db: Session = Depends(get_db)):
    build = _get_or_404(db, Build, build_id, "Build no encontrada.")
    return render(
        request,
        "admin/build_form.html",
        {"build": build, "mode": "edit", "build_id": build_id},
    )


@router.post("/builds/{build_id}/edit", name="admin.build_edit")
def build_edit(
    request: Request,
    build_id: int,
    tier: str = Form(""),
    name: str = Form(""),
    tier_emoji: str = Form("🎮"),
    budget_label: str = Form(""),
    cpu: str = Form(""),
    gpu: str = Form(""),
    ram: str = Form(""),
    storage: str = Form(""),
    performance_note: str = Form(""),
    performance_pct: str = Form("50"),
    image_url: str = Form(""),
    featured: Optional[str] = Form(None),
    active: Optional[str] = Form(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    build = _get_or_404(db, Build, build_id, "Build no encontrada.")

    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.build_edit", build_id=build_id)

    data, errors = _parse_build_form(
        _build_form_payload(
            tier, name, tier_emoji, budget_label, cpu, gpu, ram, storage,
            performance_note, performance_pct, image_url, featured, active,
        )
    )
    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request,
            "admin/build_form.html",
            {"build": data, "mode": "edit", "build_id": build_id},
            status_code=400,
        )

    for key, value in data.items():
        setattr(build, key, value)
    db.commit()
    flash(request, "Cambios guardados. La página pública ya se actualizó.", "success")
    return redirect(request, "admin.builds")


@router.post("/builds/{build_id}/toggle-active", name="admin.build_toggle_active")
def build_toggle_active(
    request: Request,
    build_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.builds")

    build = _get_or_404(db, Build, build_id, "Build no encontrada.")
    build.active = not build.active
    db.commit()
    flash(request, f"{build.name} {'activada' if build.active else 'desactivada'}.", "success")
    return redirect(request, "admin.builds")


@router.post("/builds/{build_id}/delete", name="admin.build_delete")
def build_delete(
    request: Request,
    build_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "admin.builds")

    build = _get_or_404(db, Build, build_id, "Build no encontrada.")
    db.delete(build)
    db.commit()
    flash(request, "Build eliminada permanentemente.", "success")
    return redirect(request, "admin.builds")
