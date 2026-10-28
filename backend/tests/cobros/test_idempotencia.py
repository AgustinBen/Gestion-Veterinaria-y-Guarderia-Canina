"""Tests de idempotencia."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_token(client: TestClient, username: str, password: str = "clave-de-prueba-segura") -> dict[str, str]:
    respuesta = client.post("/api/auth/login", json={"username": username, "password": password})
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_idempotencia_mismo_cuerpo_devuelve_mismo_pago(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = client.post(
        "/api/cargos",
        json={"persona_id": referencias_cobros.persona_id, "concepto": "S", "total_centavos": 30000},
        headers=headers,
    ).json()["id"]

    h1 = {**headers, "Idempotency-Key": "clave-1"}
    r1 = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO", "es_sena": True}, headers=h1)
    assert r1.status_code == 200
    pago_id = r1.json()["id"]

    r2 = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO", "es_sena": True}, headers=h1)
    assert r2.status_code == 200
    assert r2.json()["id"] == pago_id

    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers)
    assert detalle.json()["total_pagado"] == 10000


def test_idempotencia_misma_clave_distinto_cuerpo_409(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = client.post(
        "/api/cargos",
        json={"persona_id": referencias_cobros.persona_id, "concepto": "S", "total_centavos": 30000},
        headers=headers,
    ).json()["id"]

    h1 = {**headers, "Idempotency-Key": "clave-2"}
    r1 = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO"}, headers=h1)
    assert r1.status_code == 200
    r2 = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 15000, "medio": "EFECTIVO"}, headers=h1)
    assert r2.status_code == 409
