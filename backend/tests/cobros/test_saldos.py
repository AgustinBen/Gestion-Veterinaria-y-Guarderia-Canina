"""Tests de saldos por cliente y paciente."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_token(client: TestClient, username: str, password: str = "clave-de-prueba-segura") -> dict[str, str]:
    respuesta = client.post("/api/auth/login", json={"username": username, "password": password})
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_fiado_figura_con_saldo_total_y_aparece_en_cuenta_cliente(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    resp_cargo = client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Servicio",
            "total_centavos": 30000,
            "paciente_id": referencias_cobros.paciente_id,
        },
        headers=headers,
    )
    assert resp_cargo.status_code == 201

    cuenta = client.get(f"/api/personas/{referencias_cobros.persona_id}/cuenta", headers=headers)
    assert cuenta.status_code == 200
    data = cuenta.json()
    assert data["persona_id"] == referencias_cobros.persona_id
    assert data["saldo_total"] == 30000
    assert len(data["cargos"]) >= 1


def test_cuenta_por_mascota_filtra_solo_sus_cargos(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Servicio",
            "total_centavos": 30000,
            "paciente_id": referencias_cobros.paciente_id,
        },
        headers=headers,
    )
    cuenta_pac = client.get(f"/api/pacientes/{referencias_cobros.paciente_id}/cuenta", headers=headers)
    assert cuenta_pac.status_code == 200
    data = cuenta_pac.json()
    assert data["paciente_id"] == referencias_cobros.paciente_id
    assert all(c["cargo"]["paciente_id"] == referencias_cobros.paciente_id for c in data["cargos"])


def test_saldo_pendiente_suma_varios_cargos_y_no_cuenta_saldados(
    client: TestClient,
    referencias_cobros,
    db_session,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    from app.modules.cobros import service

    c1 = client.post(
        "/api/cargos",
        json={"persona_id": referencias_cobros.persona_id, "concepto": "A", "total_centavos": 10000},
        headers=headers,
    ).json()["id"]
    client.post(
        "/api/cargos",
        json={"persona_id": referencias_cobros.persona_id, "concepto": "B", "total_centavos": 20000},
        headers=headers,
    ).json()["id"]

    # Saldar c1 completo
    client.post(f"/api/cargos/{c1}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO"}, headers=headers)

    pendiente = service.saldo_pendiente(db_session, referencias_cobros.persona_id)
    assert pendiente == 20000
