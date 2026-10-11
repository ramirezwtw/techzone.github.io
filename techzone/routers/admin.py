"""Panel de administración: productos, builds, usuarios y solicitudes.

Capa HTTP. Las validaciones y las reglas están en `techzone.services`.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.core.security import require_admin, validate_csrf
from techzone.core.templating import flash, redirect, render
from techzone.models import BuildRequest
from techzone.repositories import builds as builds_repo
from techzone.repositories import products as products_repo
from techzone.repositories import users as users_repo
from techzone.services import accounts, catalog
from techzone.services import build_requests as requests_service
from techzone.services import stats

# El control de acceso se aplica a todo el router: equivale al @admin_required
# que llevaba cada vista en la versión Flask.
router = APIRouter(
    prefix="/admin",
    default_response_class=HTMLResponse,
    dependencies=[Depends(require_admin)],
)

CSRF_EXPIRED = "Tu sesión expiró, intenta de nuevo."


def _found(instance, message: str):
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    return instance


def _flash_all(request: Request, errors) -> None:
    for error in errors:
        flash(request, error, "error")


# ──────────────────────────── Dashboard ───────────────────────────────


@router.get("/", name="admin.dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    return render(request, "admin/dashboard.html", stats.admin_dashboard(db))


# ──────────────────────────── Productos ───────────────────────────────


@router.get("/products", name="admin.products")
def products(request: Request, db: Session = Depends(get_db)):
    return render(request, "admin/products.html", {"products": products_repo.list_all(db)})


def _product_form(name, brand, description, image_url, price, stock, active) -> dict:
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
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.product_new")

    data, errors = catalog.parse_product_form(
        _product_form(name, brand, description, image_url, price, stock, active)
    )
    if errors:
        _flash_all(request, errors)
        return render(
            request,
            "admin/product_form.html",
            {"product": data, "mode": "new"},
            status_code=400,
        )

    catalog.create_product(db, data)
    flash(request, "Producto creado correctamente.", "success")
    return redirect(request, "admin.products")


@router.get("/products/{product_id}/edit", name="admin.product_edit")
def product_edit_form(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = _found(products_repo.get(db, product_id), "Producto no encontrado.")
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
    product = _found(products_repo.get(db, product_id), "Producto no encontrado.")

    if not validate_csrf(request, csrf_token):
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.product_edit", product_id=product_id)

    data, errors = catalog.parse_product_form(
        _product_form(name, brand, description, image_url, price, stock, active)
    )
    if errors:
        _flash_all(request, errors)
        return render(
            request,
            "admin/product_form.html",
            {"product": data, "mode": "edit", "product_id": product_id},
            status_code=400,
        )

    catalog.update_product(db, product, data)
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
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.products")

    product = _found(products_repo.get(db, product_id), "Producto no encontrado.")
    activo = catalog.toggle_product(db, product)
    flash(request, f"{product.name} {'activado' if activo else 'desactivado'}.", "success")
    return redirect(request, "admin.products")


@router.post("/products/{product_id}/delete", name="admin.product_delete")
def product_delete(
    request: Request,
    product_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.products")

    product = _found(products_repo.get(db, product_id), "Producto no encontrado.")
    catalog.delete_product(db, product)
    flash(request, "Producto eliminado permanentemente.", "success")
    return redirect(request, "admin.products")


# ───────────────────────────── Usuarios ───────────────────────────────


@router.get("/users", name="admin.users")
def users(request: Request, db: Session = Depends(get_db)):
    return render(request, "admin/users.html", {"users": users_repo.list_all(db)})


@router.post("/users/{user_id}/toggle-active", name="admin.user_toggle_active")
def user_toggle_active(
    request: Request,
    user_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.users")

    user = _found(users_repo.get(db, user_id), "Usuario no encontrado.")
    if user.id == request.session.get("user_id"):
        flash(request, "No puedes desactivar tu propia cuenta.", "error")
        return redirect(request, "admin.users")

    activo = accounts.toggle_active(db, user)
    flash(request, f"{user.name} {'activado' if activo else 'desactivado'}.", "success")
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
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.users")

    user = _found(users_repo.get(db, user_id), "Usuario no encontrado.")
    if role not in ("user", "admin"):
        flash(request, "Rol inválido.", "error")
        return redirect(request, "admin.users")

    if user.id == request.session.get("user_id") and role != "admin":
        flash(request, "No puedes quitarte el rol de administrador a ti mismo.", "error")
        return redirect(request, "admin.users")

    accounts.change_role(db, user, role)
    flash(request, f"Rol de {user.name} actualizado a {role}.", "success")
    return redirect(request, "admin.users")


# ──────────────────────────── Solicitudes ─────────────────────────────


@router.get("/solicitudes", name="admin.solicitudes")
def solicitudes(request: Request, db: Session = Depends(get_db)):
    return render(
        request, "admin/solicitudes.html", {"requests": requests_service.all_requests(db)}
    )


def _render_solicitud(request: Request, db: Session, build_request: BuildRequest):
    return render(
        request,
        "admin/solicitud_detalle.html",
        {"r": build_request, "products": products_repo.list_active_by_name(db)},
    )


@router.get("/solicitudes/{request_id}", name="admin.solicitud_detalle")
def solicitud_detalle_form(request: Request, request_id: int, db: Session = Depends(get_db)):
    build_request = _found(requests_service.get(db, request_id), "Solicitud no encontrada.")
    return _render_solicitud(request, db, build_request)


@router.post("/solicitudes/{request_id}", name="admin.solicitud_detalle")
async def solicitud_detalle(request: Request, request_id: int, db: Session = Depends(get_db)):
    build_request = _found(requests_service.get(db, request_id), "Solicitud no encontrada.")

    # Un solo formulario con dos acciones (cambiar estado / guardar
    # recomendación) y muchos campos, así que se lee completo.
    form = await request.form()

    if not validate_csrf(request, form.get("csrf_token")):
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.solicitud_detalle", request_id=request_id)

    action = form.get("action")

    if action == "update_status":
        if requests_service.update_status(db, build_request, form.get("status")):
            flash(request, "Estado de la solicitud actualizado.", "success")
        else:
            flash(request, "Estado inválido.", "error")
        return redirect(request, "admin.solicitud_detalle", request_id=request_id)

    if action == "save_recommendation":
        errors = requests_service.save_recommendation(db, build_request, form)
        if errors:
            _flash_all(request, errors)
        else:
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
    return render(request, "admin/builds.html", {"builds": builds_repo.list_all(db)})


def _build_form(
    tier, name, tier_emoji, budget_label, cpu, gpu, ram, storage,
    performance_note, performance_pct, image_url, featured, active,
) -> dict:
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
    tier_emoji: str = Form(catalog.DEFAULT_TIER_EMOJI),
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
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.build_new")

    data, errors = catalog.parse_build_form(
        _build_form(
            tier, name, tier_emoji, budget_label, cpu, gpu, ram, storage,
            performance_note, performance_pct, image_url, featured, active,
        )
    )
    if errors:
        _flash_all(request, errors)
        return render(
            request, "admin/build_form.html", {"build": data, "mode": "new"}, status_code=400
        )

    catalog.create_build(db, data)
    flash(request, "Build creada correctamente.", "success")
    return redirect(request, "admin.builds")


@router.get("/builds/{build_id}/edit", name="admin.build_edit")
def build_edit_form(request: Request, build_id: int, db: Session = Depends(get_db)):
    build = _found(builds_repo.get(db, build_id), "Build no encontrada.")
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
    tier_emoji: str = Form(catalog.DEFAULT_TIER_EMOJI),
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
    build = _found(builds_repo.get(db, build_id), "Build no encontrada.")

    if not validate_csrf(request, csrf_token):
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.build_edit", build_id=build_id)

    data, errors = catalog.parse_build_form(
        _build_form(
            tier, name, tier_emoji, budget_label, cpu, gpu, ram, storage,
            performance_note, performance_pct, image_url, featured, active,
        )
    )
    if errors:
        _flash_all(request, errors)
        return render(
            request,
            "admin/build_form.html",
            {"build": data, "mode": "edit", "build_id": build_id},
            status_code=400,
        )

    catalog.update_build(db, build, data)
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
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.builds")

    build = _found(builds_repo.get(db, build_id), "Build no encontrada.")
    activa = catalog.toggle_build(db, build)
    flash(request, f"{build.name} {'activada' if activa else 'desactivada'}.", "success")
    return redirect(request, "admin.builds")


@router.post("/builds/{build_id}/delete", name="admin.build_delete")
def build_delete(
    request: Request,
    build_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, CSRF_EXPIRED, "error")
        return redirect(request, "admin.builds")

    build = _found(builds_repo.get(db, build_id), "Build no encontrada.")
    catalog.delete_build(db, build)
    flash(request, "Build eliminada permanentemente.", "success")
    return redirect(request, "admin.builds")
