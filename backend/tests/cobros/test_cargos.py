"""Tests de cargos."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_token(client: TestClient, username: str, password: str = "clave-de-prueba-segura") -> dict[str, str]:
    respuesta = client.post("/api/auth/login", json={"username": username, "password": password})
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_crear_cargo_devuelve_detalle_con_saldos_calculados(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Consulta",
            "total_centavos": 30000,
            "paciente_id": referencias_cobros.paciente_id,
        },
        headers=headers,
    )
    assert respuesta.status_code == 201
    data = respuesta.json()
    assert data["persona_id"] == referencias_cobros.persona_id
    assert data["paciente_id"] == referencias_cobros.paciente_id
    assert data["concepto"] == "Consulta"
    assert data["total_inicial"] == 30000

    cargo_id = data["id"]
    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers)
    assert detalle.status_code == 200
    detalle_data = detalle.json()
    assert detalle_data["total_vigente"] == 30000
    assert detalle_data["total_pagado"] == 0
    assert detalle_data["saldo"] == 30000


def test_crear_cargo_sin_token_401(client: TestClient, referencias_cobros) -> None:
    respuesta = client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Consulta",
            "total_centavos": 10000,
        },
    )
    assert respuesta.status_code == 401


def test_obtener_cargo_inexistente_404(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = client.get("/api/cargos/999999", headers=headers)
    assert respuesta.status_code == 404
