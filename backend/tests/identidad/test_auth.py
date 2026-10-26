"""Tests de login, logout y usuario actual."""

from sqlalchemy.orm import Session

from app.modules.identidad import security
from app.modules.identidad.models import Usuario
from app.modules.identidad.permisos import Rol


def test_login_normaliza_username_y_devuelve_token(
    client, crear_usuario, login, password_prueba
) -> None:
    usuario = crear_usuario("  Ana  ", rol=Rol.DUENIO, password=password_prueba)

    respuesta = login("  ANA  ", password_prueba)

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["token_type"] == "bearer"
    assert datos["rol"] == "DUENIO"
    assert "password" not in datos
    assert datos["access_token"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {datos['access_token']}"},
    )

    assert me.status_code == 200
    assert me.json() == {
        "id": usuario.id,
        "username": "ana",
        "rol": "DUENIO",
        "empleado_id": None,
    }


def test_login_rechazos_son_uniformes(
    crear_usuario, login, password_prueba
) -> None:
    activa = crear_usuario("activa", password=password_prueba)
    inactiva = crear_usuario("inactiva", password=password_prueba, activo=False)

    casos = [
        ("no_existe", password_prueba),
        (activa.username, "clave-incorrecta"),
        (inactiva.username, password_prueba),
        (inactiva.username, "clave-incorrecta"),
    ]

    respuestas = [login(username, password) for username, password in casos]

    assert all(respuesta.status_code == 401 for respuesta in respuestas)
    assert all(
        respuesta.json() == {"detail": "Credenciales inválidas"}
        for respuesta in respuestas
    )
    assert all("access_token" not in respuesta.json() for respuesta in respuestas)


def test_password_no_se_guarda_ni_se_expone(
    db_session: Session, crear_usuario, password_prueba
) -> None:
    usuario = crear_usuario("ana", password=password_prueba)

    db_session.expire_all()
    guardado = db_session.get(Usuario, usuario.id)

    assert guardado is not None
    assert guardado.password_hash != password_prueba
    assert password_prueba not in guardado.password_hash
    assert security.verificar_password(guardado.password_hash, password_prueba)


def test_logout_requiere_token_y_devuelve_204(
    client, crear_usuario, auth_de
) -> None:
    usuario = crear_usuario("ana")

    sin_token = client.post("/api/auth/logout")
    con_token = client.post("/api/auth/logout", headers=auth_de(usuario))

    assert sin_token.status_code == 401
    assert con_token.status_code == 204
    assert con_token.content == b""


def test_me_devuelve_empleado_id_y_cualquier_rol(
    client, crear_usuario, auth_de
) -> None:
    usuario = crear_usuario(
        "veterinaria",
        rol=Rol.VETERINARIO,
        empleado_id=123,
    )

    respuesta = client.get("/api/auth/me", headers=auth_de(usuario))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": usuario.id,
        "username": "veterinaria",
        "rol": "VETERINARIO",
        "empleado_id": 123,
    }
