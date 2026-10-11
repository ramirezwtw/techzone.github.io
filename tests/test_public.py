"""Páginas públicas: home, legales, builds y archivos estáticos."""

from database import SessionLocal
from models import Build, Product


def test_home_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "TechZone" in response.text


def test_home_lista_catalogo_y_builds(client):
    response = client.get("/")
    assert "AMD Ryzen 9" in response.text
    assert "Gamer Intermedio" in response.text


def test_home_oculta_productos_y_builds_inactivos(client):
    # Nombres que no aparecen en las especificaciones de otras builds.
    with SessionLocal() as session:
        product = session.query(Product).filter(Product.name == "Gabinete Gamer ATX").one()
        product.active = False
        build = session.query(Build).filter(Build.name == "Gamer Intermedio").one()
        build.active = False
        session.commit()

    response = client.get("/")
    assert "Gabinete Gamer ATX" not in response.text
    assert "Gamer Intermedio" not in response.text
    assert "Gamer Inicial" in response.text  # las activas siguen ahí


def test_home_muestra_estadisticas_de_comunidad(client):
    response = client.get("/")
    assert response.status_code == 200
    # Con la base recién sembrada hay 1 usuario (el admin) y ningún post.
    assert "com-stat-num" in response.text


def test_url_for_static_resuelve(client):
    response = client.get("/")
    assert '/static/css/style.css' in response.text
    assert '/static/img/logo-techzone.png' in response.text


def test_static_se_sirve(client):
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/img/logo-techzone.png").status_code == 200


def test_paginas_legales(client):
    for slug, titulo in [
        ("privacidad", "Privacidad"),
        ("terminos", "Términos"),
        ("cookies", "Cookies"),
    ]:
        response = client.get(f"/legal/{slug}")
        assert response.status_code == 200, slug
        assert titulo in response.text


def test_pagina_legal_inexistente_404(client):
    assert client.get("/legal/noexiste").status_code == 404


def test_detalle_de_build(client):
    response = client.get("/builds/1")
    assert response.status_code == 200
    assert "Gamer Inicial" in response.text


def test_build_inexistente_404(client):
    assert client.get("/builds/999").status_code == 404


def test_build_inactiva_404(client):
    with SessionLocal() as session:
        build = session.get(Build, 1)
        build.active = False
        session.commit()

    assert client.get("/builds/1").status_code == 404


def test_pagina_de_error_es_html(client):
    response = client.get("/legal/noexiste")
    assert "text/html" in response.headers["content-type"]
    assert "Página no encontrada" in response.text
