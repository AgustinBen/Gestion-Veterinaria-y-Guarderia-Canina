from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_token(
    client: TestClient, username: str, password: str = "clave-de-prueba-segura"
) -> dict[str, str]:
    respuesta = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_deuda_no_bloquea_nuevo_cargo_ni_pago(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    deuda = client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Fiado",
            "total_centavos": 12000,
        },
        headers=headers,
    )
    assert deuda.status_code == 201
    nuevo = client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Nuevo servicio",
            "total_centavos": 3000,
        },
        headers=headers,
    )
    assert nuevo.status_code == 201
    pago = client.post(
        f"/api/cargos/{deuda.json()['id']}/pagos",
        json={"monto_centavos": 1000, "medio": "EFECTIVO"},
        headers=headers,
    )
    assert pago.status_code == 200
