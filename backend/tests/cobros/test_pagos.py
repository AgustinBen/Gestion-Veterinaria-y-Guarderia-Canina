"""Tests de pagos y señas."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_token(client: TestClient, username: str, password: str = "clave-de-prueba-segura") -> dict[str, str]:
    respuesta = client.post("/api/auth/login", json={"username": username, "password": password})
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _crear_cargo(client: TestClient, headers: dict[str, str], referencias_cobros, total_centavos: int = 30000) -> int:
    respuesta = client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Servicio",
            "total_centavos": total_centavos,
            "paciente_id": referencias_cobros.paciente_id,
        },
        headers=headers,
    )
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def test_ejemplo_central_sena_y_pago(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros, total_centavos=30000)

    # Seña de $10.000
    sena = client.post(
        f"/api/cargos/{cargo_id}/pagos",
        json={"monto_centavos": 10000, "medio": "EFECTIVO", "es_sena": True},
        headers=headers,
    )
    assert sena.status_code == 200
    assert sena.json()["es_sena"] is True

    # Pago de $15.000
    pago = client.post(
        f"/api/cargos/{cargo_id}/pagos",
        json={"monto_centavos": 15000, "medio": "DEBITO", "es_sena": False},
        headers=headers,
    )
    assert pago.status_code == 200

    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers)
    assert detalle.status_code == 200
    data = detalle.json()
    assert data["total_pagado"] == 25000
    assert data["saldo"] == 5000


def test_pago_exacto_del_saldo_deja_saldo_cero(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros, total_centavos=30000)
    client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO", "es_sena": True}, headers=headers)
    client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 15000, "medio": "EFECTIVO"}, headers=headers)
    resp = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 5000, "medio": "EFECTIVO"}, headers=headers)
    assert resp.status_code == 200
    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers)
    assert detalle.json()["saldo"] == 0


def test_pago_mayor_al_saldo_422_con_saldo_restante(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros, total_centavos=30000)
    client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO", "es_sena": True}, headers=headers)
    client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 15000, "medio": "EFECTIVO"}, headers=headers)
    resp = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 5001, "medio": "EFECTIVO"}, headers=headers)
    assert resp.status_code == 422
    assert "5000" in resp.text


def test_pago_sobre_cargo_ya_saldado_422(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros, total_centavos=10000)
    client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO"}, headers=headers)
    resp = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 1000, "medio": "EFECTIVO"}, headers=headers)
    assert resp.status_code == 422


def test_sena_parcial_saldo_restante(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros, total_centavos=30000)
    resp = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 1000, "medio": "EFECTIVO", "es_sena": True}, headers=headers)
    assert resp.status_code == 200
    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers)
    assert detalle.json()["saldo"] == 29000


def test_sena_cero_o_negativa_422(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros, total_centavos=30000)
    resp = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 0, "medio": "EFECTIVO", "es_sena": True}, headers=headers)
    assert resp.status_code == 422
    resp2 = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": -100, "medio": "EFECTIVO", "es_sena": True}, headers=headers)
    assert resp2.status_code == 422
