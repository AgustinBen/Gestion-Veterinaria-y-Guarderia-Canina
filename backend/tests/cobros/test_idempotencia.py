"""Tests de idempotencia."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.cobros import repository, service


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


def test_misma_clave_con_lectura_desactualizada_devuelve_el_pago_existente(
    db_session: Session,
    referencias_cobros,
    monkeypatch,
) -> None:
    cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Servicio",
        total_centavos=30000,
        usuario_id=referencias_cobros.usuario_id,
    )
    pago = service.registrar_pago(
        db_session,
        cargo_id=cargo.id,
        monto_centavos=10000,
        medio="EFECTIVO",
        usuario_id=referencias_cobros.usuario_id,
        clave_idempotencia="clave-carrera",
    )

    original = repository.obtener_pago_por_clave_idempotencia
    llamadas = {"n": 0}

    def lectura_desactualizada(db: Session, clave: str):
        llamadas["n"] += 1
        # Simula el pedido simultáneo que no ve el pago del otro hilo.
        if llamadas["n"] <= 2:
            return None
        return original(db, clave)

    monkeypatch.setattr(
        repository, "obtener_pago_por_clave_idempotencia", lectura_desactualizada
    )

    repetido = service.registrar_pago(
        db_session,
        cargo_id=cargo.id,
        monto_centavos=10000,
        medio="EFECTIVO",
        usuario_id=referencias_cobros.usuario_id,
        clave_idempotencia="clave-carrera",
    )

    assert repetido.id == pago.id
    assert len(repository.pagos_de_cargo(db_session, cargo.id)) == 1
