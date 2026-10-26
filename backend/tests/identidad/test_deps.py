"""Tests de las dependencias de autenticación y autorización."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.modules.identidad.deps import get_current_user, require_acceso, require_role
from app.modules.identidad.permisos import Nivel, Recurso, Rol
from app.modules.identidad.schemas import UsuarioActual

app_prueba = FastAPI()


@app_prueba.get("/me")
def _me(usuario: UsuarioActual = Depends(get_current_user)):
    return {"id": usuario.id, "username": usuario.username, "rol": usuario.rol}


@app_prueba.get("/solo-duenio")
def _solo_duenio(usuario: UsuarioActual = Depends(require_role(Rol.DUENIO))):
    return {"rol": usuario.rol}


@app_prueba.get("/sin-roles")
def _sin_roles(usuario: UsuarioActual = Depends(require_role())):
    return {"rol": usuario.rol}


@app_prueba.get("/padron/lectura")
def _padron_lectura(
    usuario: UsuarioActual = Depends(require_acceso(Recurso.PADRON, Nivel.LECTURA)),
):
    return {"rol": usuario.rol}


@app_prueba.post("/padron/escritura")
def _padron_escritura(
    usuario: UsuarioActual = Depends(require_acceso(Recurso.PADRON, Nivel.ESCRITURA)),
):
    return {"rol": usuario.rol}


@app_prueba.post("/deudas/escritura")
def _deudas_escritura(
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.DEUDAS_COBROS, Nivel.ESCRITURA)
    ),
):
    return {"rol": usuario.rol}


@app_prueba.get("/emergencia/lectura")
def _emergencia_lectura(
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.EMERGENCIA, Nivel.LECTURA)
    ),
):
    return {"rol": usuario.rol}


@pytest.fixture
def client_prueba(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app_prueba.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app_prueba) as client:
            yield client
    finally:
        app_prueba.dependency_overrides.clear()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _alterar_firma(token: str) -> str:
    cabecera, payload, firma = token.split(".")
    primer_caracter = "A" if firma[0] != "A" else "B"
    return f"{cabecera}.{payload}.{primer_caracter}{firma[1:]}"


def test_sin_token_401(client_prueba: TestClient) -> None:
    respuesta = client_prueba.get("/me")

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "No autenticado"}
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_basic_auth_no_autentica(client_prueba: TestClient) -> None:
    respuesta = client_prueba.get("/me", headers={"Authorization": "Basic abc"})

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "No autenticado"}


def test_token_invalido_401(client_prueba: TestClient) -> None:
    respuesta = client_prueba.get("/me", headers=_auth("no-es-un-token"))

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "No autenticado"}


def test_token_alterado_401(
    client_prueba: TestClient, crear_usuario, token_de
) -> None:
    usuario = crear_usuario("ana")

    respuesta = client_prueba.get(
        "/me", headers=_auth(_alterar_firma(token_de(usuario)))
    )

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "No autenticado"}


def test_token_vencido_401(client_prueba: TestClient, crear_usuario, token_de) -> None:
    usuario = crear_usuario("ana")
    vencido = datetime.now(timezone.utc) - timedelta(
        minutes=get_settings().session_minutes + 1
    )

    respuesta = client_prueba.get(
        "/me", headers=_auth(token_de(usuario, ahora=vencido))
    )

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "No autenticado"}


def test_usuario_inexistente_401(client_prueba: TestClient, token_de) -> None:
    class _UsuarioFalso:
        id = 999_999
        rol = Rol.DUENIO

    respuesta = client_prueba.get("/me", headers=_auth(token_de(_UsuarioFalso())))

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "No autenticado"}


def test_usuario_inactivo_401(
    client_prueba: TestClient, crear_usuario, token_de
) -> None:
    usuario = crear_usuario("inactiva", activo=False)

    respuesta = client_prueba.get("/me", headers=_auth(token_de(usuario)))

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "No autenticado"}


def test_usuario_valido_200(client_prueba: TestClient, crear_usuario, token_de) -> None:
    usuario = crear_usuario("ana", rol=Rol.DUENIO)

    respuesta = client_prueba.get("/me", headers=_auth(token_de(usuario)))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": usuario.id,
        "username": "ana",
        "rol": "DUENIO",
    }


def test_activo_se_consulta_en_cada_pedido(
    client_prueba: TestClient, crear_usuario, token_de, db_session: Session
) -> None:
    usuario = crear_usuario("ana")
    token = token_de(usuario)

    assert client_prueba.get("/me", headers=_auth(token)).status_code == 200

    usuario.activo = False
    db_session.commit()
    assert client_prueba.get("/me", headers=_auth(token)).status_code == 401

    usuario.activo = True
    db_session.commit()
    assert client_prueba.get("/me", headers=_auth(token)).status_code == 200


def test_rol_de_la_db_manda_sobre_el_token(
    client_prueba: TestClient, crear_usuario, token_de, db_session: Session
) -> None:
    usuario = crear_usuario("ana", rol=Rol.DUENIO)
    token = token_de(usuario)

    usuario.rol = Rol.PERSONAL
    db_session.commit()

    assert client_prueba.get("/me", headers=_auth(token)).json()["rol"] == "PERSONAL"
    assert client_prueba.get("/solo-duenio", headers=_auth(token)).status_code == 403


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        (Rol.DUENIO, 200),
        (Rol.PERSONAL, 403),
        (Rol.VETERINARIO, 403),
    ],
)
def test_require_role_duenio(
    client_prueba: TestClient, crear_usuario, token_de, rol: Rol, esperado: int
) -> None:
    usuario = crear_usuario(f"user_{rol.value}", rol=rol)

    respuesta = client_prueba.get(
        "/solo-duenio", headers=_auth(token_de(usuario))
    )

    assert respuesta.status_code == esperado


@pytest.mark.parametrize("rol", list(Rol))
def test_require_role_sin_roles_deniega(
    client_prueba: TestClient, crear_usuario, token_de, rol: Rol
) -> None:
    usuario = crear_usuario(f"user_{rol.value}", rol=rol)

    respuesta = client_prueba.get("/sin-roles", headers=_auth(token_de(usuario)))

    assert respuesta.status_code == 403


@pytest.mark.parametrize(
    ("rol", "metodo", "ruta", "esperado"),
    [
        (Rol.DUENIO, "get", "/padron/lectura", 200),
        (Rol.PERSONAL, "get", "/padron/lectura", 200),
        (Rol.VETERINARIO, "get", "/padron/lectura", 200),
        (Rol.VETERINARIO, "post", "/padron/escritura", 403),
        (Rol.PERSONAL, "post", "/padron/escritura", 200),
        (Rol.PERSONAL, "post", "/deudas/escritura", 200),
        (Rol.VETERINARIO, "post", "/deudas/escritura", 403),
        (Rol.PERSONAL, "get", "/emergencia/lectura", 403),
        (Rol.DUENIO, "get", "/emergencia/lectura", 200),
    ],
)
def test_require_acceso_representativo(
    client_prueba: TestClient,
    crear_usuario,
    token_de,
    rol: Rol,
    metodo: str,
    ruta: str,
    esperado: int,
) -> None:
    usuario = crear_usuario(f"user_{rol.value}", rol=rol)

    respuesta = client_prueba.request(
        metodo.upper(), ruta, headers=_auth(token_de(usuario))
    )

    assert respuesta.status_code == esperado


def test_401_es_uniforme(
    client_prueba: TestClient, crear_usuario, token_de
) -> None:
    inactiva = crear_usuario("inactiva", activo=False)
    vencido = datetime.now(timezone.utc) - timedelta(
        minutes=get_settings().session_minutes + 1
    )

    respuestas = [
        client_prueba.get("/me"),
        client_prueba.get("/me", headers=_auth("no-es-un-token")),
        client_prueba.get("/me", headers=_auth(token_de(inactiva))),
        client_prueba.get("/me", headers=_auth(token_de(inactiva, ahora=vencido))),
    ]

    assert all(respuesta.status_code == 401 for respuesta in respuestas)
    assert all(
        respuesta.json() == {"detail": "No autenticado"} for respuesta in respuestas
    )
