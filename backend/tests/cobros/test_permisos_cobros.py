"""Tests de permisos de cobros."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_token(client: TestClient, username: str, password: str = "clave-de-prueba-segura") -> dict[str, str]:
    respuesta = client.post("/api/auth/login", json={"username": username, "password": password})
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_matriz_sin_token_401(client: TestClient, referencias_cobros) -> None:
    assert client.get("/api/medios-pago").status_code == 401
    assert client.get("/api/cargos/1").status_code == 401
    assert client.get(f"/api/personas/{referencias_cobros.persona_id}/cuenta").status_code == 401


def test_personal_y_duenio_pueden_en_deudas_cobros(
    client: TestClient,
    referencias_cobros,
    db_session,
) -> None:
    from app.modules.identidad import service as identidad_service
    from app.modules.identidad.permisos import Rol
    from app.modules.identidad.schemas import UsuarioCrear

    # Personal
    identidad_service.crear_usuario(db_session, UsuarioCrear(username="personal-c", password="clave-de-prueba-segura", rol=Rol.PERSONAL))
    h_p = _auth_token(client, "personal-c")
    r = client.get("/api/medios-pago", headers=h_p)
    assert r.status_code == 200


def test_veterinario_403_en_deudas_cobros(
    client: TestClient,
    referencias_cobros,
    db_session,
) -> None:
    from app.modules.identidad import service as identidad_service
    from app.modules.identidad.permisos import Rol
    from app.modules.identidad.schemas import UsuarioCrear

    identidad_service.crear_usuario(db_session, UsuarioCrear(username="vet-c", password="clave-de-prueba-segura", rol=Rol.VETERINARIO))
    h_v = _auth_token(client, "vet-c")
    r = client.get("/api/medios-pago", headers=h_v)
    assert r.status_code == 403
    r2 = client.post(
        "/api/cargos",
        json={"persona_id": referencias_cobros.persona_id, "concepto": "X", "total_centavos": 1000},
        headers=h_v,
    )
    assert r2.status_code == 403
