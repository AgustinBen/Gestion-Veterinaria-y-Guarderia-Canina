"""Permisos de finanzas: gastos a externos solo para el Dueño (T-22)."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear


def _auth_token(
    client: TestClient, username: str, password: str = "clave-de-prueba-segura"
) -> dict[str, str]:
    respuesta = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _cuerpo_gasto(referencias_cobros) -> dict:
    return {
        "empleado_id": referencias_cobros.empleado_id,
        "descripcion": "Cirugía",
        "monto_centavos": 40000,
        "fecha": date.today().isoformat(),
    }


def test_sin_token_401(client: TestClient, referencias_cobros) -> None:
    assert client.get("/api/gastos-externos").status_code == 401
    assert client.get("/api/gastos-externos/1").status_code == 401
    assert (
        client.post("/api/gastos-externos", json=_cuerpo_gasto(referencias_cobros)).status_code
        == 401
    )
    assert (
        client.post("/api/gastos-externos/1/anular", json={"motivo": "x"}).status_code
        == 401
    )


@pytest.mark.parametrize(
    "username,rol",
    [
        ("personal-f", Rol.PERSONAL),
        ("veterinario-f", Rol.VETERINARIO),
    ],
)
def test_personal_y_veterinario_403(
    client: TestClient,
    db_session,
    referencias_cobros,
    username: str,
    rol: Rol,
) -> None:
    identidad_service.crear_usuario(
        db_session,
        UsuarioCrear(username=username, password="clave-de-prueba-segura", rol=rol),
    )
    headers = _auth_token(client, username)

    assert client.get("/api/gastos-externos", headers=headers).status_code == 403
    assert client.get("/api/gastos-externos/1", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/gastos-externos",
            json=_cuerpo_gasto(referencias_cobros),
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/gastos-externos/1/anular", json={"motivo": "x"}, headers=headers
        ).status_code
        == 403
    )


def test_duenio_puede_listar_y_crear(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")

    assert client.get("/api/gastos-externos", headers=headers).status_code == 200
    creado = client.post(
        "/api/gastos-externos",
        json=_cuerpo_gasto(referencias_cobros),
        headers=headers,
    )
    assert creado.status_code == 201
    gasto_id = creado.json()["id"]

    assert (
        client.get(f"/api/gastos-externos/{gasto_id}", headers=headers).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/gastos-externos/{gasto_id}/anular",
            json={"motivo": "Error de carga"},
            headers=headers,
        ).status_code
        == 200
    )
