"""Panel de administración: productos, builds, usuarios y solicitudes."""

from decimal import Decimal

from conftest import ADMIN_EMAIL
from techzone.core.database import SessionLocal
from helpers import (
    BUILD_FORM,
    PRODUCT_FORM,
    create_build_request,
    create_user,
    flashes,
    post_form,
    stats,
)
from techzone.models import Build, BuildRequest, Product, User


def test_todas_las_secciones_cargan(admin_client):
    for path in [
        "/admin/",
        "/admin/products",
        "/admin/products/new",
        "/admin/builds",
        "/admin/builds/new",
        "/admin/users",
        "/admin/solicitudes",
    ]:
        assert admin_client.get(path).status_code == 200, path


def test_contadores_del_dashboard(admin_client):
    response = admin_client.get("/admin/")
    # Orden de la plantilla: usuarios, admins, productos, activos, sin stock, pendientes.
    assert stats(response.text) == ["1", "1", "9", "9", "1", "0"]


def test_dashboard_cuenta_solicitudes_pendientes(admin_client):
    user_id = create_user()
    create_build_request(user_id)
    create_build_request(user_id, status="Finalizado")
    assert stats(admin_client.get("/admin/").text)[5] == "1"


def test_menu_marca_la_seccion_activa(admin_client):
    response = admin_client.get("/admin/products")
    assert 'admin-nav-link active">Productos' in response.text


# ──────────────────────────── productos ──────────────────────────


def test_crear_producto(admin_client):
    response = post_form(admin_client, "/admin/products/new", PRODUCT_FORM)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/products"

    with SessionLocal() as session:
        product = session.query(Product).filter(Product.name == "Cooler AIO 360").one()
        assert product.price == Decimal("199.90")
        assert product.stock == 5
        assert product.active is True

    assert "Cooler AIO 360" in admin_client.get("/admin/products").text
    assert "Cooler AIO 360" in admin_client.get("/").text


def test_crear_producto_sin_nombre(admin_client):
    datos = dict(PRODUCT_FORM, name="", brand="")
    response = post_form(admin_client, "/admin/products/new", datos)
    assert response.status_code == 400
    mensajes = flashes(response.text)
    assert "El nombre del producto es obligatorio." in mensajes
    assert "La marca/categoría es obligatoria." in mensajes


def test_crear_producto_con_precio_invalido(admin_client):
    response = post_form(admin_client, "/admin/products/new", dict(PRODUCT_FORM, price="abc"))
    assert response.status_code == 400
    assert "El precio debe ser un número válido." in flashes(response.text)


def test_crear_producto_con_valores_negativos(admin_client):
    response = post_form(
        admin_client, "/admin/products/new", dict(PRODUCT_FORM, price="-5", stock="-2")
    )
    assert response.status_code == 400
    mensajes = flashes(response.text)
    assert "El precio no puede ser negativo." in mensajes
    assert "El stock no puede ser negativo." in mensajes


def test_csrf_invalido_no_crea_nada(admin_client):
    response = admin_client.post(
        "/admin/products/new",
        data=dict(PRODUCT_FORM, csrf_token="falso"),
        follow_redirects=False,
    )
    assert response.status_code == 303
    with SessionLocal() as session:
        assert session.query(Product).filter(Product.name == "Cooler AIO 360").count() == 0


def test_editar_producto(admin_client):
    response = post_form(
        admin_client,
        "/admin/products/1/edit",
        dict(PRODUCT_FORM, name="AMD Ryzen 9 7950X", price="649.99"),
    )
    assert response.status_code == 303
    with SessionLocal() as session:
        product = session.get(Product, 1)
        assert product.name == "AMD Ryzen 9 7950X"
        assert product.price == Decimal("649.99")


def test_editar_producto_inexistente_404(admin_client):
    assert admin_client.get("/admin/products/999/edit").status_code == 404


def test_activar_y_desactivar_producto(admin_client):
    post_form(admin_client, "/admin/products/1/toggle-active", token_from="/admin/products")
    with SessionLocal() as session:
        assert session.get(Product, 1).active is False

    post_form(admin_client, "/admin/products/1/toggle-active", token_from="/admin/products")
    with SessionLocal() as session:
        assert session.get(Product, 1).active is True


def test_eliminar_producto(admin_client):
    response = post_form(
        admin_client, "/admin/products/1/delete", token_from="/admin/products"
    )
    assert response.status_code == 303
    with SessionLocal() as session:
        assert session.get(Product, 1) is None


# ────────────────────────────── builds ───────────────────────────


def test_crear_build(admin_client):
    response = post_form(
        admin_client, "/admin/builds/new", dict(BUILD_FORM, name="Gamer Extremo")
    )
    assert response.status_code == 303
    with SessionLocal() as session:
        assert session.query(Build).filter(Build.name == "Gamer Extremo").count() == 1


def test_crear_build_sin_datos_obligatorios(admin_client):
    datos = dict(BUILD_FORM, tier="", name="", budget_label="")
    response = post_form(admin_client, "/admin/builds/new", datos)
    assert response.status_code == 400
    mensajes = flashes(response.text)
    assert "El nivel (tier) es obligatorio." in mensajes
    assert "El nombre de la build es obligatorio." in mensajes
    assert "Indica el rango de presupuesto." in mensajes


def test_porcentaje_de_rendimiento_se_acota_a_100(admin_client):
    post_form(admin_client, "/admin/builds/1/edit", dict(BUILD_FORM, performance_pct="150"))
    with SessionLocal() as session:
        assert session.get(Build, 1).performance_pct == 100


def test_porcentaje_de_rendimiento_invalido(admin_client):
    response = post_form(
        admin_client, "/admin/builds/1/edit", dict(BUILD_FORM, performance_pct="muchísimo")
    )
    assert response.status_code == 400
    assert "El porcentaje de rendimiento debe ser un número entero." in flashes(response.text)


def test_editar_build_actualiza_el_sitio_publico(admin_client):
    post_form(admin_client, "/admin/builds/1/edit", dict(BUILD_FORM, name="Gamer Inicial PRO"))
    assert "Gamer Inicial PRO" in admin_client.get("/").text
    assert "Gamer Inicial PRO" in admin_client.get("/builds/1").text


def test_desactivar_y_eliminar_build(admin_client):
    post_form(admin_client, "/admin/builds/1/toggle-active", token_from="/admin/builds")
    with SessionLocal() as session:
        assert session.get(Build, 1).active is False

    post_form(admin_client, "/admin/builds/1/delete", token_from="/admin/builds")
    with SessionLocal() as session:
        assert session.get(Build, 1) is None


# ───────────────────────────── usuarios ──────────────────────────


def test_listado_de_usuarios(admin_client):
    create_user()
    response = admin_client.get("/admin/users")
    assert ADMIN_EMAIL in response.text
    assert "ana@example.com" in response.text


def test_desactivar_usuario(admin_client):
    user_id = create_user()
    post_form(admin_client, f"/admin/users/{user_id}/toggle-active", token_from="/admin/users")
    with SessionLocal() as session:
        assert session.get(User, user_id).active is False


def test_el_admin_no_puede_desactivarse(admin_client):
    with SessionLocal() as session:
        admin_id = session.query(User).filter(User.email == ADMIN_EMAIL).one().id

    post_form(admin_client, f"/admin/users/{admin_id}/toggle-active", token_from="/admin/users")
    response = admin_client.get("/admin/users")
    assert "No puedes desactivar tu propia cuenta." in flashes(response.text)
    with SessionLocal() as session:
        assert session.get(User, admin_id).active is True


def test_cambiar_rol_de_usuario(admin_client):
    user_id = create_user()
    post_form(
        admin_client,
        f"/admin/users/{user_id}/role",
        {"role": "admin"},
        token_from="/admin/users",
    )
    with SessionLocal() as session:
        assert session.get(User, user_id).role == "admin"


def test_rol_invalido(admin_client):
    user_id = create_user()
    post_form(
        admin_client,
        f"/admin/users/{user_id}/role",
        {"role": "superusuario"},
        token_from="/admin/users",
    )
    assert "Rol inválido." in flashes(admin_client.get("/admin/users").text)
    with SessionLocal() as session:
        assert session.get(User, user_id).role == "user"


def test_el_admin_no_se_quita_su_propio_rol(admin_client):
    with SessionLocal() as session:
        admin_id = session.query(User).filter(User.email == ADMIN_EMAIL).one().id

    post_form(
        admin_client,
        f"/admin/users/{admin_id}/role",
        {"role": "user"},
        token_from="/admin/users",
    )
    assert "No puedes quitarte el rol de administrador a ti mismo." in flashes(
        admin_client.get("/admin/users").text
    )
    with SessionLocal() as session:
        assert session.get(User, admin_id).role == "admin"


# ─────────────────────────── solicitudes ─────────────────────────


def test_listado_de_solicitudes_muestra_al_usuario(admin_client):
    user_id = create_user()
    create_build_request(user_id)
    response = admin_client.get("/admin/solicitudes")
    assert "Ana Pérez" in response.text
    assert "ana@example.com" in response.text


def test_el_admin_ve_los_componentes_actuales(admin_client):
    request_id = create_build_request(
        create_user(), has_components=True, current_cpu="Ryzen 3 3200G", current_ram="8 GB DDR4"
    )
    response = admin_client.get(f"/admin/solicitudes/{request_id}")
    assert "Ryzen 3 3200G" in response.text
    assert "8 GB DDR4" in response.text


def test_cambiar_estado_de_solicitud(admin_client):
    request_id = create_build_request(create_user())
    response = post_form(
        admin_client,
        f"/admin/solicitudes/{request_id}",
        {"action": "update_status", "status": "Contactado"},
    )
    assert response.status_code == 303
    with SessionLocal() as session:
        assert session.get(BuildRequest, request_id).status == "Contactado"


def test_estado_invalido_no_se_guarda(admin_client):
    request_id = create_build_request(create_user())
    post_form(
        admin_client,
        f"/admin/solicitudes/{request_id}",
        {"action": "update_status", "status": "Inventado"},
    )
    with SessionLocal() as session:
        assert session.get(BuildRequest, request_id).status == "Pendiente"


def test_guardar_recomendacion(admin_client):
    request_id = create_build_request(create_user())
    response = post_form(
        admin_client,
        f"/admin/solicitudes/{request_id}",
        {
            "action": "save_recommendation",
            "rec_cpu": "Ryzen 7 7700X",
            "rec_gpu": "RTX 4070",
            "rec_explanation": "Equilibrio ideal para 1440p y compilación.",
            "rec_price_estimate": "4200000",
        },
    )
    assert response.status_code == 303

    with SessionLocal() as session:
        build_request = session.get(BuildRequest, request_id)
        assert build_request.rec_cpu == "Ryzen 7 7700X"
        assert build_request.rec_price_estimate == Decimal("4200000")
        assert build_request.has_recommendation is True
        # Pasa sola de 'Pendiente' a 'Recomendación lista'.
        assert build_request.status == "Recomendación lista"


def test_recomendacion_sin_explicacion_no_se_guarda(admin_client):
    request_id = create_build_request(create_user())
    post_form(
        admin_client,
        f"/admin/solicitudes/{request_id}",
        {"action": "save_recommendation", "rec_cpu": "Ryzen 7 7700X", "rec_explanation": ""},
    )
    assert "Agrega una explicación de la recomendación." in flashes(
        admin_client.get(f"/admin/solicitudes/{request_id}").text
    )
    with SessionLocal() as session:
        build_request = session.get(BuildRequest, request_id)
        assert build_request.rec_cpu == ""
        assert build_request.has_recommendation is False


def test_precio_estimado_invalido_no_se_guarda(admin_client):
    request_id = create_build_request(create_user())
    post_form(
        admin_client,
        f"/admin/solicitudes/{request_id}",
        {
            "action": "save_recommendation",
            "rec_explanation": "Una explicación válida.",
            "rec_price_estimate": "cuatro millones",
        },
    )
    assert "El precio estimado debe ser un número válido." in flashes(
        admin_client.get(f"/admin/solicitudes/{request_id}").text
    )
    with SessionLocal() as session:
        assert session.get(BuildRequest, request_id).has_recommendation is False


def test_solicitud_inexistente_404(admin_client):
    assert admin_client.get("/admin/solicitudes/999").status_code == 404
