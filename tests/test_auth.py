"""Registro, login, sesión, CSRF, verificación de correo y recuperación."""

from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD
from techzone.database import SessionLocal
from helpers import create_user, csrf_token, flashes, login, post_form
from techzone.models import AuthToken, User


# ───────────────────────────── login ─────────────────────────────


def test_login_muestra_formulario(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert csrf_token(response.text)


def test_login_con_password_incorrecta(client):
    response = login(client, ADMIN_EMAIL, "incorrecta")
    assert response.status_code == 401
    assert "incorrectos" in response.text


def test_login_con_correo_inexistente(client):
    response = login(client, "nadie@example.com", "lo-que-sea")
    assert response.status_code == 401


def test_login_de_cuenta_desactivada(client):
    create_user(active=False)
    response = login(client, USER_EMAIL, USER_PASSWORD)
    assert response.status_code == 403
    assert "desactivada" in response.text


def test_login_admin_va_al_panel(client):
    response = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/"


def test_login_usuario_va_al_home(client):
    create_user()
    response = login(client, USER_EMAIL, USER_PASSWORD)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_login_respeta_next_interno(client):
    create_user()
    response = login(client, USER_EMAIL, USER_PASSWORD, next_url="/comunidad/nueva")
    assert response.headers["location"] == "/comunidad/nueva"


def test_login_ignora_next_externo(client):
    create_user()
    response = login(client, USER_EMAIL, USER_PASSWORD, next_url="https://evil.example.com")
    assert response.headers["location"] == "/"


def test_login_con_csrf_invalido(client):
    client.get("/login")
    response = client.post(
        "/login",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "csrf_token": "falso"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_logout_limpia_la_sesion(admin_client):
    assert admin_client.get("/admin/").status_code == 200
    response = admin_client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert admin_client.get("/admin/", follow_redirects=False).status_code == 303


# ─────────────────────── control de acceso ───────────────────────


def test_ruta_privada_sin_sesion_redirige_con_next(client):
    response = client.get("/perfil/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Fperfil%2F"


def test_mensaje_al_redirigir_al_login(client):
    response = client.get("/perfil/")
    assert "Debes iniciar sesión para continuar." in flashes(response.text)


def test_usuario_normal_no_entra_al_admin(user_client):
    assert user_client.get("/admin/").status_code == 403


# ──────────────────────────── registro ───────────────────────────


def test_registro_valida_los_campos(client):
    response = post_form(
        client,
        "/registro",
        {"name": "A", "email": "no-es-correo", "password": "123", "password_confirm": "456"},
    )
    assert response.status_code == 400
    mensajes = flashes(response.text)
    assert "Ingresa tu nombre completo." in mensajes
    assert "Ingresa un correo electrónico válido." in mensajes
    assert "La contraseña debe tener al menos 8 caracteres." in mensajes
    assert "Las contraseñas no coinciden." in mensajes


def test_registro_rechaza_correo_duplicado(client):
    create_user()
    response = post_form(
        client,
        "/registro",
        {
            "name": "Ana Pérez",
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
            "password_confirm": USER_PASSWORD,
        },
    )
    assert response.status_code == 400
    assert "Ya existe una cuenta registrada con ese correo." in flashes(response.text)


def test_registro_crea_la_cuenta_e_inicia_sesion(client):
    response = post_form(
        client,
        "/registro",
        {
            "name": "Ana Pérez",
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
            "password_confirm": USER_PASSWORD,
        },
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == USER_EMAIL).one()
        assert user.role == "user"
        assert user.active is True
        assert user.email_verified is False
        assert user.password_hash != USER_PASSWORD  # nunca en texto plano
        assert user.check_password(USER_PASSWORD)

    # Quedó con sesión abierta: una ruta privada ya no redirige.
    assert client.get("/perfil/").status_code == 200


def test_registro_emite_token_de_verificacion(client):
    post_form(
        client,
        "/registro",
        {
            "name": "Ana Pérez",
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
            "password_confirm": USER_PASSWORD,
        },
    )
    with SessionLocal() as session:
        token = (
            session.query(AuthToken)
            .filter(AuthToken.purpose == AuthToken.PURPOSE_VERIFY)
            .one()
        )
        assert token.is_valid


# ─────────────────── verificación de correo ──────────────────────


def _token_de(purpose):
    with SessionLocal() as session:
        token = session.query(AuthToken).filter(AuthToken.purpose == purpose).one()
        return token.token


def test_verificacion_de_correo(client):
    post_form(
        client,
        "/registro",
        {
            "name": "Ana Pérez",
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
            "password_confirm": USER_PASSWORD,
        },
    )
    token = _token_de(AuthToken.PURPOSE_VERIFY)

    response = client.get(f"/verify-email/{token}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    with SessionLocal() as session:
        assert session.query(User).filter(User.email == USER_EMAIL).one().email_verified


def test_verificacion_con_token_invalido(client):
    response = client.get("/verify-email/token-que-no-existe", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_reenviar_verificacion(user_client):
    response = post_form(user_client, "/reenviar-verificacion", token_from="/perfil/")
    assert response.status_code == 303
    with SessionLocal() as session:
        assert (
            session.query(AuthToken)
            .filter(AuthToken.purpose == AuthToken.PURPOSE_VERIFY)
            .count()
            == 1
        )


# ────────────────── recuperación de contraseña ───────────────────


def test_olvide_contrasena_emite_token(client):
    create_user()
    response = post_form(client, "/olvide-contrasena", {"email": USER_EMAIL})
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    with SessionLocal() as session:
        assert (
            session.query(AuthToken)
            .filter(AuthToken.purpose == AuthToken.PURPOSE_RESET)
            .count()
            == 1
        )


def test_olvide_contrasena_no_revela_si_el_correo_existe(client):
    response = post_form(client, "/olvide-contrasena", {"email": "nadie@example.com"})
    assert response.status_code == 303
    with SessionLocal() as session:
        assert session.query(AuthToken).count() == 0


def test_reset_de_contrasena(client):
    create_user()
    post_form(client, "/olvide-contrasena", {"email": USER_EMAIL})
    token = _token_de(AuthToken.PURPOSE_RESET)

    assert client.get(f"/restablecer-contrasena/{token}").status_code == 200

    response = post_form(
        client,
        f"/restablecer-contrasena/{token}",
        {"password": "nueva12345", "password_confirm": "nueva12345"},
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    assert login(client, USER_EMAIL, "nueva12345").status_code == 303


def test_reset_valida_las_contrasenas(client):
    create_user()
    post_form(client, "/olvide-contrasena", {"email": USER_EMAIL})
    token = _token_de(AuthToken.PURPOSE_RESET)

    response = post_form(
        client,
        f"/restablecer-contrasena/{token}",
        {"password": "corta", "password_confirm": "otra"},
    )
    assert response.status_code == 400


def test_token_de_reset_es_de_un_solo_uso(client):
    create_user()
    post_form(client, "/olvide-contrasena", {"email": USER_EMAIL})
    token = _token_de(AuthToken.PURPOSE_RESET)
    post_form(
        client,
        f"/restablecer-contrasena/{token}",
        {"password": "nueva12345", "password_confirm": "nueva12345"},
    )

    response = client.get(f"/restablecer-contrasena/{token}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/olvide-contrasena"


def test_nuevo_token_invalida_el_anterior(client):
    create_user()
    post_form(client, "/olvide-contrasena", {"email": USER_EMAIL})
    primero = _token_de(AuthToken.PURPOSE_RESET)
    post_form(client, "/olvide-contrasena", {"email": USER_EMAIL})
    segundo = _token_de(AuthToken.PURPOSE_RESET)

    assert primero != segundo
    response = client.get(f"/restablecer-contrasena/{primero}", follow_redirects=False)
    assert response.status_code == 303
