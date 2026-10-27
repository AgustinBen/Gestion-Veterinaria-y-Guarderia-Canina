"""Tests de mascotas, edad calculada y catálogos (RN-05, RN-09)."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.modules.padron import service


def _crear_titular(crear_persona_api, duenio, persona_payload) -> int:
    respuesta = crear_persona_api(duenio, persona_payload())
    assert respuesta.status_code == 201
    return int(respuesta.json()["id"])


def test_paciente_con_edad_calculada_y_sin_factor_cupo(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    titular_id = _crear_titular(crear_persona_api, duenio, persona_payload)

    respuesta = client.post(
        "/api/pacientes",
        json={
            "nombre": "Firulais",
            "especie_id": especie_perro,
            "fecha_nacimiento_aprox": "2000-01-01",
            "titular_persona_id": titular_id,
        },
        headers=auth(duenio),
    )

    assert respuesta.status_code == 201
    datos = respuesta.json()
    hoy = date.today()
    meses = (hoy.year - 2000) * 12 + (hoy.month - 1)
    assert datos["edad_anios"] == meses // 12
    assert datos["edad_meses"] == meses % 12
    assert "factor_cupo" not in datos


def test_paciente_no_acepta_edad_en_el_cuerpo(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    titular_id = _crear_titular(crear_persona_api, duenio, persona_payload)

    respuesta = client.post(
        "/api/pacientes",
        json={
            "nombre": "Firulais",
            "especie_id": especie_perro,
            "titular_persona_id": titular_id,
            "edad_anios": 3,
        },
        headers=auth(duenio),
    )

    assert respuesta.status_code == 422


def test_mascota_sin_especie_422(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
) -> None:
    titular_id = _crear_titular(crear_persona_api, duenio, persona_payload)

    respuesta = client.post(
        "/api/pacientes",
        json={"nombre": "Firulais", "titular_persona_id": titular_id},
        headers=auth(duenio),
    )

    assert respuesta.status_code == 422


def test_titular_principal_en_la_ficha(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    titular_id = _crear_titular(crear_persona_api, duenio, persona_payload)
    creado = client.post(
        "/api/pacientes",
        json={
            "nombre": "Firulais",
            "especie_id": especie_perro,
            "titular_persona_id": titular_id,
        },
        headers=auth(duenio),
    )
    assert creado.status_code == 201

    titulares = client.get(
        f"/api/pacientes/{creado.json()['id']}/titulares",
        headers=auth(duenio),
    )

    assert titulares.status_code == 200
    assert len(titulares.json()) == 1
    assert titulares.json()[0]["persona_id"] == titular_id
    assert titulares.json()[0]["principal"] is True


def test_alta_rapida_de_raza_es_idempotente(
    client: TestClient, auth, duenio, especie_perro: int
) -> None:
    primera = client.post(
        "/api/razas",
        json={"nombre": "Ovejero", "especie_id": especie_perro},
        headers=auth(duenio),
    )
    segunda = client.post(
        "/api/razas",
        json={"nombre": "ovejero", "especie_id": especie_perro},
        headers=auth(duenio),
    )

    assert primera.status_code == 201
    assert segunda.status_code == 201
    assert primera.json()["id"] == segunda.json()["id"]

    listado = client.get(
        f"/api/razas?especie_id={especie_perro}", headers=auth(duenio)
    )
    assert listado.status_code == 200
    assert len(listado.json()) == 1


def test_obtener_paciente_del_service_no_expone_factor_cupo(
    db_session,
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    titular_id = _crear_titular(crear_persona_api, duenio, persona_payload)
    creado = client.post(
        "/api/pacientes",
        json={
            "nombre": "Firulais",
            "especie_id": especie_perro,
            "titular_persona_id": titular_id,
        },
        headers=auth(duenio),
    )
    assert creado.status_code == 201

    detalle = service.obtener_paciente(db_session, creado.json()["id"])

    assert detalle is not None
    assert "factor_cupo" not in detalle.model_dump()
