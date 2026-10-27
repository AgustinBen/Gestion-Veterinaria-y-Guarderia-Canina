"""Tests de la matriz de roles aplicada al padrón (RN-40)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_veterinario_lee_pero_no_escribe(
    client: TestClient, auth, veterinario, persona_payload
) -> None:
    lectura = client.get("/api/personas", headers=auth(veterinario))
    escritura = client.post(
        "/api/personas", json=persona_payload(), headers=auth(veterinario)
    )

    assert lectura.status_code == 200
    assert escritura.status_code == 403


def test_personal_puede_crear_personas(
    client: TestClient, auth, personal, persona_payload
) -> None:
    respuesta = client.post(
        "/api/personas", json=persona_payload(), headers=auth(personal)
    )

    assert respuesta.status_code == 201


def test_sin_token_401(client: TestClient) -> None:
    respuesta = client.get("/api/personas")

    assert respuesta.status_code == 401


def test_personal_no_puede_crear_empleados(
    client: TestClient, auth, personal
) -> None:
    respuesta = client.post(
        "/api/empleados",
        json={
            "persona": {
                "nombre": "Carlos",
                "apellido": "Vet",
                "dni": "31111222",
                "telefonos": ["11 4444-5555"],
            }
        },
        headers=auth(personal),
    )

    assert respuesta.status_code == 403


def test_duenio_crea_empleado_y_los_tres_roles_leen(
    client: TestClient, auth, duenio, personal, veterinario
) -> None:
    creado = client.post(
        "/api/empleados",
        json={
            "persona": {
                "nombre": "Carlos",
                "apellido": "Vet",
                "dni": "31111222",
                "telefonos": ["11 4444-5555"],
            },
            "es_veterinario": True,
            "especialidad": "Clínica",
        },
        headers=auth(duenio),
    )

    assert creado.status_code == 201
    persona_id = creado.json()["persona_id"]
    assert isinstance(persona_id, int)
    for usuario in (duenio, personal, veterinario):
        listado = client.get("/api/empleados", headers=auth(usuario))
        assert listado.status_code == 200
        assert [empleado["persona_id"] for empleado in listado.json()] == [persona_id]


def test_veterinario_no_puede_crear_razas(
    client: TestClient, auth, veterinario, especie_perro: int
) -> None:
    respuesta = client.post(
        "/api/razas",
        json={"nombre": "Ovejero", "especie_id": especie_perro},
        headers=auth(veterinario),
    )

    assert respuesta.status_code == 403
