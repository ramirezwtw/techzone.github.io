"""API JSON v1: lo que consume el frontend Astro."""

from helpers import create_post, create_user
from techzone.core.database import SessionLocal
from techzone.models import Build, Comment, Product


# ──────────────────────────────── catálogo ──────────────────────────────────


def test_productos_activos(client):
    response = client.get("/api/v1/catalog/products")
    assert response.status_code == 200

    productos = response.json()
    assert len(productos) == 9
    primero = productos[0]
    assert primero["name"] == "AMD Ryzen 9"
    assert primero["brand"] == "AMD"
    assert primero["price"] == 549.99  # el precio viaja como número
    assert primero["stock"] == 18
    # El DTO no expone columnas internas.
    assert "active" not in primero
    assert "created_at" not in primero


def test_productos_inactivos_no_salen(client):
    with SessionLocal() as session:
        session.query(Product).filter(Product.id == 1).one().active = False
        session.commit()

    nombres = [p["name"] for p in client.get("/api/v1/catalog/products").json()]
    assert "AMD Ryzen 9" not in nombres
    assert len(nombres) == 8


def test_builds_activas(client):
    builds = client.get("/api/v1/catalog/builds").json()
    assert [b["name"] for b in builds] == [
        "Gamer Inicial",
        "Gamer Intermedio",
        "Gamer Profesional",
    ]
    intermedia = builds[1]
    assert intermedia["featured"] is True
    assert intermedia["performance_pct"] == 72
    assert intermedia["tier_emoji"] == "💜"


def test_detalle_de_build(client):
    build = client.get("/api/v1/catalog/builds/1").json()
    assert build["id"] == 1
    assert build["cpu"] == "AMD Ryzen 5 5600 / Intel i5-12400F"


def test_build_inexistente(client):
    response = client.get("/api/v1/catalog/builds/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Build no encontrada."


def test_build_inactiva_no_se_expone(client):
    with SessionLocal() as session:
        session.get(Build, 1).active = False
        session.commit()

    assert client.get("/api/v1/catalog/builds/1").status_code == 404


# ──────────────────────────────── comunidad ─────────────────────────────────


def test_publicaciones_con_autor_y_contadores(client):
    user_id = create_user()
    post_id = create_post(user_id)
    with SessionLocal() as session:
        session.add(Comment(post_id=post_id, user_id=user_id, content="Yo iría por la 4070."))
        session.commit()

    posts = client.get("/api/v1/community/posts").json()
    assert len(posts) == 1
    assert posts[0]["author"] == "Ana Pérez"
    assert posts[0]["comment_count"] == 1
    assert posts[0]["like_count"] == 0
    assert "content" not in posts[0]  # el listado no trae el cuerpo


def test_detalle_de_publicacion_con_comentarios(client):
    user_id = create_user()
    post_id = create_post(user_id)
    with SessionLocal() as session:
        session.add(Comment(post_id=post_id, user_id=user_id, content="Yo iría por la 4070."))
        session.commit()

    post = client.get(f"/api/v1/community/posts/{post_id}").json()
    assert post["title"] == "¿Vale la pena una RTX 4070?"
    assert post["content"] == "Dudo entre 4070 y 7800 XT."
    assert [c["content"] for c in post["comments"]] == ["Yo iría por la 4070."]
    assert post["comments"][0]["author"] == "Ana Pérez"


def test_publicacion_inexistente(client):
    assert client.get("/api/v1/community/posts/999").status_code == 404


def test_la_api_no_cuenta_vistas(client):
    """Leer por la API no debe inflar el contador del foro."""
    post_id = create_post(create_user())
    client.get(f"/api/v1/community/posts/{post_id}")
    client.get(f"/api/v1/community/posts/{post_id}")

    from techzone.models import Post

    with SessionLocal() as session:
        assert session.get(Post, post_id).views == 0


def test_estadisticas_de_comunidad(client):
    create_post(create_user())
    stats = client.get("/api/v1/community/stats").json()
    assert stats == {"users": 2, "posts": 1, "comments": 0, "requests": 0}


# ───────────────────────────────── contenido ────────────────────────────────


def test_payload_del_home(client):
    create_post(create_user())
    home = client.get("/api/v1/home").json()

    assert set(home) == {"products", "builds", "recent_posts", "stats"}
    assert len(home["products"]) == 9
    assert len(home["builds"]) == 3
    assert len(home["recent_posts"]) == 1
    assert home["stats"] == {"users": 2, "posts": 1, "comments": 0}


def test_el_home_trae_como_maximo_tres_publicaciones(client):
    user_id = create_user()
    for i in range(5):
        create_post(user_id, title=f"Publicación número {i}")

    assert len(client.get("/api/v1/home").json()["recent_posts"]) == 3


def test_paginas_legales(client):
    for slug in ["privacidad", "terminos", "cookies"]:
        page = client.get(f"/api/v1/legal/{slug}").json()
        assert page["slug"] == slug
        assert page["title"]
        assert len(page["body"]) >= 1


def test_pagina_legal_inexistente(client):
    assert client.get("/api/v1/legal/noexiste").status_code == 404


# ─────────────────────────────────── OpenAPI ────────────────────────────────


def test_la_api_esta_documentada(client):
    esquema = client.get("/openapi.json").json()
    rutas = esquema["paths"]
    assert "/api/v1/catalog/products" in rutas
    assert "/api/v1/community/posts/{post_id}" in rutas
    assert rutas["/api/v1/home"]["get"]["summary"] == "Todo lo que necesita el home"


# ──────────────────────────────── sesión ────────────────────────────────────


def test_me_sin_sesion(client):
    assert client.get("/api/v1/me").json() == {
        "authenticated": False,
        "name": None,
        "role": None,
        "is_admin": False,
        "flashes": [],
    }


def test_me_con_usuario(user_client):
    cuerpo = user_client.get("/api/v1/me").json()
    assert cuerpo["authenticated"] is True
    assert cuerpo["name"] == "Ana Pérez"
    assert cuerpo["role"] == "user"
    assert cuerpo["is_admin"] is False


def test_me_con_admin(admin_client):
    cuerpo = admin_client.get("/api/v1/me").json()
    assert cuerpo["is_admin"] is True
    assert cuerpo["role"] == "admin"


def test_el_extracto_recorta_el_contenido(client):
    largo = "x" * 200
    create_post(create_user(), content=largo)
    post = client.get("/api/v1/community/posts").json()[0]
    assert post["excerpt"] == "x" * 150 + "..."
    assert len(post["excerpt"]) == 153


def test_el_extracto_no_recorta_lo_corto(client):
    create_post(create_user(), content="Corto y al grano.")
    assert client.get("/api/v1/community/posts").json()[0]["excerpt"] == "Corto y al grano."


def test_me_entrega_los_flashes_una_sola_vez(client):
    """Un redirect del backend deja un mensaje; el frontend lo recoge al pintar."""
    client.get("/perfil/", follow_redirects=False)  # deja "Debes iniciar sesión..."

    flashes = client.get("/api/v1/me").json()["flashes"]
    assert flashes == [
        {"category": "error", "message": "Debes iniciar sesión para continuar."}
    ]
    # Ya consumidos: la siguiente lectura viene vacía.
    assert client.get("/api/v1/me").json()["flashes"] == []


def test_csrf_entrega_un_token_estable(client):
    primero = client.get("/api/v1/csrf").json()["csrf_token"]
    assert len(primero) == 64
    # El token vive en la sesión: no cambia entre llamadas.
    assert client.get("/api/v1/csrf").json()["csrf_token"] == primero


def test_el_token_de_la_api_sirve_para_un_formulario(user_client):
    """El token que da la API es el mismo que valida el backend en un POST."""
    token = user_client.get("/api/v1/csrf").json()["csrf_token"]
    response = user_client.post(
        "/comunidad/nueva",
        data={
            "title": "Publicado desde el frontend",
            "content": "Contenido suficientemente largo para pasar la validación.",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_el_detalle_dice_si_el_visitante_dio_like(user_client):
    post_id = create_post(create_user(email="otro@example.com", name="Otro"))
    assert user_client.get(f"/api/v1/community/posts/{post_id}").json()["liked"] is False

    token = user_client.get("/api/v1/csrf").json()["csrf_token"]
    user_client.post(
        f"/comunidad/{post_id}/like", data={"csrf_token": token}, follow_redirects=False
    )
    assert user_client.get(f"/api/v1/community/posts/{post_id}").json()["liked"] is True


def test_el_like_de_otro_no_marca_al_visitante(client):
    post_id = create_post(create_user())
    assert client.get(f"/api/v1/community/posts/{post_id}").json()["liked"] is False
