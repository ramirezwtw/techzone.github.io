"""Foro de la comunidad: publicaciones, comentarios, likes y vistas."""

from conftest import USER_EMAIL
from techzone.database import SessionLocal
from helpers import create_post, create_user, flashes, post_form
from techzone.models import Comment, Post, PostLike, User

NUEVO_POST = {
    "title": "¿Vale la pena una RTX 4070?",
    "content": "Estoy dudando entre la 4070 y la 7800 XT para jugar en 1440p.",
}


def _user_id(email=USER_EMAIL):
    with SessionLocal() as session:
        return session.query(User).filter(User.email == email).one().id


def test_comunidad_carga_sin_sesion(client):
    response = client.get("/comunidad/")
    assert response.status_code == 200


def test_estadisticas_de_la_comunidad(client):
    user_id = create_user()
    post_id = create_post(user_id)
    with SessionLocal() as session:
        session.add(Comment(post_id=post_id, user_id=user_id, content="Yo iría por la 4070."))
        session.commit()

    response = client.get("/comunidad/")
    assert "RTX 4070" in response.text
    assert "1 respuestas" in response.text


def test_publicar_requiere_sesion(client):
    response = client.get("/comunidad/nueva", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Fcomunidad%2Fnueva"


def test_crear_publicacion(user_client):
    response = post_form(user_client, "/comunidad/nueva", NUEVO_POST)
    assert response.status_code == 303
    assert response.headers["location"] == "/comunidad/1"

    with SessionLocal() as session:
        post = session.query(Post).one()
        assert post.title == NUEVO_POST["title"]
        assert post.user_id == _user_id()
        assert post.views == 0


def test_validaciones_al_publicar(user_client):
    response = post_form(user_client, "/comunidad/nueva", {"title": "Hola", "content": "corto"})
    assert response.status_code == 400
    mensajes = flashes(response.text)
    assert "El título debe tener al menos 5 caracteres." in mensajes
    assert "Cuéntanos un poco más (mínimo 20 caracteres)." in mensajes
    with SessionLocal() as session:
        assert session.query(Post).count() == 0


def test_el_detalle_cuenta_las_vistas(client):
    post_id = create_post(create_user())
    client.get(f"/comunidad/{post_id}")
    client.get(f"/comunidad/{post_id}")
    with SessionLocal() as session:
        assert session.get(Post, post_id).views == 2


def test_publicacion_inexistente_404(client):
    assert client.get("/comunidad/999").status_code == 404


def test_comentar(user_client):
    post_id = create_post(_user_id())
    response = post_form(
        user_client,
        f"/comunidad/{post_id}/comentar",
        {"content": "Yo iría por la 4070."},
        token_from=f"/comunidad/{post_id}",
    )
    assert response.status_code == 303

    detalle = user_client.get(f"/comunidad/{post_id}")
    assert "Yo iría por la 4070." in detalle.text
    assert "Comentario publicado." in flashes(detalle.text)


def test_comentario_vacio_no_se_guarda(user_client):
    post_id = create_post(_user_id())
    post_form(
        user_client,
        f"/comunidad/{post_id}/comentar",
        {"content": " "},
        token_from=f"/comunidad/{post_id}",
    )
    with SessionLocal() as session:
        assert session.query(Comment).count() == 0


def test_comentar_requiere_sesion(client):
    post_id = create_post(create_user())
    response = client.post(
        f"/comunidad/{post_id}/comentar",
        data={"content": "Hola", "csrf_token": "x"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_like_y_quitar_like(user_client):
    post_id = create_post(_user_id())

    post_form(
        user_client, f"/comunidad/{post_id}/like", token_from=f"/comunidad/{post_id}"
    )
    with SessionLocal() as session:
        assert session.query(PostLike).count() == 1
    assert "❤️ 1" in user_client.get(f"/comunidad/{post_id}").text

    post_form(
        user_client, f"/comunidad/{post_id}/like", token_from=f"/comunidad/{post_id}"
    )
    with SessionLocal() as session:
        assert session.query(PostLike).count() == 0


def test_las_publicaciones_recientes_salen_en_el_home(client):
    create_post(create_user())
    response = client.get("/")
    assert "RTX 4070" in response.text


def test_el_home_solo_muestra_tres_publicaciones(client):
    user_id = create_user()
    for i in range(5):
        create_post(user_id, title=f"Publicación número {i}")
    response = client.get("/")
    assert sum(f"Publicación número {i}" in response.text for i in range(5)) == 3
