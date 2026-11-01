"""Tests de reversos."""

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


def test_reverso_devuelve_saldo_a_estado_anterior_sin_borrar_original(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers_duenio = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers_duenio, referencias_cobros, total_centavos=30000)
    client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO", "es_sena": True}, headers=headers_duenio)
    pago_resp = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 15000, "medio": "DEBITO"}, headers=headers_duenio)
    assert pago_resp.status_code == 200
    pago_id = pago_resp.json()["id"]

    detalle_antes = client.get(f"/api/cargos/{cargo_id}", headers=headers_duenio).json()
    assert detalle_antes["saldo"] == 5000

    rev = client.post(f"/api/pagos/{pago_id}/revertir", json={"motivo": "Error de carga"}, headers=headers_duenio)
    assert rev.status_code == 200
    reverso = rev.json()
    assert reverso["tipo"] == "REVERSO"
    assert reverso["pago_revertido_id"] == pago_id
    assert reverso["motivo"] == "Error de carga"

    detalle_despues = client.get(f"/api/cargos/{cargo_id}", headers=headers_duenio).json()
    assert detalle_despues["saldo"] == 20000

    # Original sigue existiendo
    cuenta = client.get(f"/api/personas/{referencias_cobros.persona_id}/cuenta", headers=headers_duenio).json()
    pagos_ids = []
    for c in cuenta["cargos"]:
        for p in c["pagos"]:
            pagos_ids.append(p["id"])
    assert pago_id in pagos_ids


def test_revertir_dos_veces_mismo_pago_409(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers_duenio = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers_duenio, referencias_cobros, total_centavos=10000)
    pago_resp = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO"}, headers=headers_duenio)
    pago_id = pago_resp.json()["id"]
    r1 = client.post(f"/api/pagos/{pago_id}/revertir", json={"motivo": "Error"}, headers=headers_duenio)
    assert r1.status_code == 200
    r2 = client.post(f"/api/pagos/{pago_id}/revertir", json={"motivo": "Error"}, headers=headers_duenio)
    assert r2.status_code == 409


def test_personal_en_revertir_403(
    client: TestClient,
    referencias_cobros,
    db_session,
) -> None:
    from app.modules.identidad import service as identidad_service
    from app.modules.identidad.permisos import Rol
    from app.modules.identidad.schemas import UsuarioCrear

    headers_duenio = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers_duenio, referencias_cobros, total_centavos=10000)
    pago_resp = client.post(f"/api/cargos/{cargo_id}/pagos", json={"monto_centavos": 10000, "medio": "EFECTIVO"}, headers=headers_duenio)
    pago_id = pago_resp.json()["id"]

    identidad_service.crear_usuario(db_session, UsuarioCrear(username="personal-cobros", password="clave-de-prueba-segura", rol=Rol.PERSONAL))
    headers_personal = _auth_token(client, "personal-cobros")
    resp = client.post(f"/api/pagos/{pago_id}/revertir", json={"motivo": "Error"}, headers=headers_personal)
    assert resp.status_code == 403
