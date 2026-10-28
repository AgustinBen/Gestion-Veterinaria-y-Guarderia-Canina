"""Fixtures compartidos de los tests del módulo padrón."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import parametros
from app.core.config import get_settings
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear, UsuarioPublico
from app.modules.padron.seed import (
    sembrar_especies_tamanios_tipo_contacto,
    sembrar_parametros_padron,
)

PASSWORD_PRUEBA = "clave-de-prueba-segura"


@pytest.fixture(autouse=True)
def _secret_key_de_pruebas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        get_settings(),
        "secret_key",
        "clave-de-pruebas-de-padron-con-mas-de-32-bytes",
    )


@pytest.fixture(autouse=True)
def _entorno_padron(db_session: Session) -> Generator[None, None, None]:
    """Parámetros del módulo, con caché limpia por test."""
    parametros._limpiar_cache()
    sembrar_parametros_padron(db_session)
    yield
    parametros._limpiar_cache()


@pytest.fixture
def catalogos(db_session: Session) -> None:
    """Especies, tamaños y tipos de contacto que usan los endpoints."""
    sembrar_especies_tamanios_tipo_contacto(db_session)


@pytest.fixture
def crear_usuario(db_session: Session):
    def _crear(
        username: str, rol: Rol = Rol.PERSONAL
    ) -> UsuarioPublico:
        return identidad_service.crear_usuario(
            db_session,
            UsuarioCrear(username=username, password=PASSWORD_PRUEBA, rol=rol),
        )

    return _crear


@pytest.fixture
def duenio(crear_usuario) -> UsuarioPublico:
    return crear_usuario("duenio", Rol.DUENIO)


@pytest.fixture
def personal(crear_usuario) -> UsuarioPublico:
    return crear_usuario("personal", Rol.PERSONAL)


@pytest.fixture
def veterinario(crear_usuario) -> UsuarioPublico:
    return crear_usuario("veterinario", Rol.VETERINARIO)


@pytest.fixture
def auth(client: TestClient):
    """Header Authorization real pasando por el login."""

    def _auth(usuario: UsuarioPublico) -> dict[str, str]:
        respuesta = client.post(
            "/api/auth/login",
            json={"username": usuario.username, "password": PASSWORD_PRUEBA},
        )
        assert respuesta.status_code == 200
        token = respuesta.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth


@pytest.fixture
def persona_payload():
    """Datos base de una persona; cada test los ajusta sin repetir todo."""

    def _payload(**cambios: object) -> dict[str, object]:
        datos: dict[str, object] = {
            "nombre": "Ana",
            "apellido": "Perez",
            "dni": "30111222",
            "telefonos": ["11 4444-5555"],
        }
        datos.update(cambios)
        return datos

    return _payload


@pytest.fixture
def crear_persona_api(client: TestClient, auth):
    def _crear(
        usuario: UsuarioPublico,
        payload: dict[str, object],
    ):
        return client.post("/api/personas", json=payload, headers=auth(usuario))

    return _crear


@pytest.fixture
def especie_perro(client: TestClient, auth, duenio, catalogos) -> int:
    respuesta = client.get("/api/especies", headers=auth(duenio))
    assert respuesta.status_code == 200
    for especie in respuesta.json():
        if especie["nombre"] == "Perro":
            return int(especie["id"])
    raise AssertionError("No se sembró la especie Perro")
