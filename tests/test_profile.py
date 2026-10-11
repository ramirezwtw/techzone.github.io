"""Perfil del usuario y formulario 'Ayúdame a armar mi PC'."""

from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD
from techzone.database import SessionLocal
from helpers import ARMAR_PC_FORM, create_build_request, flashes, login, post_form
from techzone.models import BuildRequest, User


def test_perfil_carga(user_client):
    response = user_client.get("/perfil/")
    assert response.status_code == 200
    assert "Ana Pérez" in response.text


def test_perfil_lista_las_solicitudes(user_client):
    with SessionLocal() as session:
        user_id = session.query(User).filter(User.email == USER_EMAIL).one().id
    create_build_request(user_id)
    response = user_client.get("/perfil/")
    assert "Gaming" in response.text


def test_formulario_de_armado_carga(user_client):
    response = user_client.get("/perfil/armar-pc")
    assert response.status_code == 200
    assert "Gaming" in response.text
    assert "Fortnite" in response.text


def test_precarga_desde_una_build(user_client):
    response = user_client.get(
        "/perfil/armar-pc?purpose=Gaming&budget=$4.000.000&build=Gamer%20Intermedio"
    )
    assert response.status_code == 200
    assert "$4.000.000" in response.text
    assert "Gamer Intermedio" in response.text


def test_solicitud_valida_se_guarda(user_client):
    response = post_form(user_client, "/perfil/armar-pc", ARMAR_PC_FORM)
    assert response.status_code == 303
    assert response.headers["location"] == "/perfil/"

    with SessionLocal() as session:
        build_request = session.query(BuildRequest).one()
        assert build_request.purpose == "Gaming,Programación"
        assert build_request.games == "GTA VI,Valorant,Elden Ring"
        assert build_request.programs == "Blender"
        assert build_request.peripherals == "Monitor,Teclado"
        assert build_request.budget == "$3.000.000 - $5.000.000"
        assert build_request.has_components is True
        assert build_request.current_cpu == "Ryzen 3 3200G"
        assert build_request.pref_color == "Otro"
        assert build_request.pref_color_other == "Blanco"
        assert build_request.status == "Pendiente"


def test_presupuesto_personalizado(user_client):
    datos = dict(
        ARMAR_PC_FORM, budget_range="Otro (especificar)", budget_custom="$4.200.000"
    )
    post_form(user_client, "/perfil/armar-pc", datos)
    with SessionLocal() as session:
        assert session.query(BuildRequest).one().budget == "$4.200.000"


def test_sin_componentes_no_guarda_los_campos_actuales(user_client):
    datos = dict(ARMAR_PC_FORM, has_components="no")
    post_form(user_client, "/perfil/armar-pc", datos)
    with SessionLocal() as session:
        build_request = session.query(BuildRequest).one()
        assert build_request.has_components is False
        assert build_request.current_cpu == ""


def test_solicitud_sin_uso_ni_descripcion(user_client):
    datos = dict(ARMAR_PC_FORM)
    datos["purpose"] = []
    datos["description"] = "corto"
    datos["budget_range"] = ""
    response = post_form(user_client, "/perfil/armar-pc", datos)
    assert response.status_code == 400
    mensajes = flashes(response.text)
    assert "Selecciona para qué necesitas tu PC (al menos una opción)." in mensajes
    assert "Indica tu presupuesto aproximado." in mensajes
    assert any("mínimo 20 caracteres" in m for m in mensajes)
    with SessionLocal() as session:
        assert session.query(BuildRequest).count() == 0


def test_uso_otro_exige_detalle(user_client):
    datos = dict(ARMAR_PC_FORM, purpose=["Otro"], purpose_other="")
    response = post_form(user_client, "/perfil/armar-pc", datos)
    assert response.status_code == 400
    assert any("Otro" in m for m in flashes(response.text))


def test_color_otro_exige_detalle(user_client):
    datos = dict(ARMAR_PC_FORM, pref_color="Otro", pref_color_other="")
    response = post_form(user_client, "/perfil/armar-pc", datos)
    assert response.status_code == 400
    assert "Especifica el color preferido." in flashes(response.text)


def test_el_formulario_conserva_lo_escrito_tras_un_error(user_client):
    datos = dict(ARMAR_PC_FORM, description="corto")
    response = post_form(user_client, "/perfil/armar-pc", datos)
    assert response.status_code == 400
    assert "Ryzen 3 3200G" in response.text
    assert "Elden Ring" in response.text


def test_detalle_de_solicitud_propia(user_client):
    post_form(user_client, "/perfil/armar-pc", ARMAR_PC_FORM)
    response = user_client.get("/perfil/solicitudes/1")
    assert response.status_code == 200
    assert "Gaming,Programación" in response.text
    assert "GTA VI,Valorant,Elden Ring" in response.text
    assert "Monitor,Teclado" in response.text


def test_no_se_puede_ver_la_solicitud_de_otro(user_client, other_user_id):
    request_id = create_build_request(other_user_id)
    assert user_client.get(f"/perfil/solicitudes/{request_id}").status_code == 403


def test_solicitud_inexistente_404(user_client):
    assert user_client.get("/perfil/solicitudes/999").status_code == 404


def test_el_usuario_ve_la_recomendacion_del_admin(user_client):
    post_form(user_client, "/perfil/armar-pc", ARMAR_PC_FORM)
    user_client.get("/logout")

    login(user_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    post_form(
        user_client,
        "/admin/solicitudes/1",
        {
            "action": "save_recommendation",
            "rec_cpu": "Ryzen 7 7700X",
            "rec_explanation": "Equilibrio ideal para 1440p.",
        },
    )
    user_client.get("/logout")

    login(user_client, USER_EMAIL, USER_PASSWORD)
    response = user_client.get("/perfil/solicitudes/1")
    assert "Ryzen 7 7700X" in response.text
    assert "Equilibrio ideal para 1440p." in response.text
