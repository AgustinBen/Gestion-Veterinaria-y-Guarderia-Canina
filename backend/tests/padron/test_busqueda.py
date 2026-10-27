"""Tests de búsqueda rápida y paginación estable."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _crear(
    crear_persona_api,
    duenio,
    persona_payload,
    *,
    nombre: str,
    apellido: str,
    dni: str,
    telefono: str,
) -> dict:
    respuesta = crear_persona_api(
        duenio,
        persona_payload(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            telefonos=[telefono],
        ),
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def test_busqueda_por_apellido_parcial(
    client: TestClient, auth, duenio, crear_persona_api, persona_payload
) -> None:
    _crear(
        crear_persona_api,
        duenio,
        persona_payload,
        nombre="Ana",
        apellido="Perez",
        dni="30111222",
        telefono="11 4444-5555",
    )
    _crear(
        crear_persona_api,
        duenio,
        persona_payload,
        nombre="Beto",
        apellido="Gomez",
        dni="30999888",
        telefono="11 6666-7777",
    )

    respuesta = client.get("/api/personas?q=Pere", headers=auth(duenio))

    assert respuesta.status_code == 200
    assert [persona["apellido"] for persona in respuesta.json()] == ["Perez"]


def test_busqueda_por_dni_y_telefono_en_otro_formato(
    client: TestClient, auth, duenio, crear_persona_api, persona_payload
) -> None:
    creada = _crear(
        crear_persona_api,
        duenio,
        persona_payload,
        nombre="Ana",
        apellido="Perez",
        dni="30111222",
        telefono="11 4444-5555",
    )

    por_dni = client.get("/api/personas?q=30111222", headers=auth(duenio))
    por_telefono = client.get(
        "/api/personas?q=+54 9 11 4444-5555", headers=auth(duenio)
    )
    por_parametro = client.get(
        "/api/personas?telefono=11 4444-5555", headers=auth(duenio)
    )

    assert por_dni.status_code == 200
    assert [persona["id"] for persona in por_dni.json()] == [creada["id"]]
    assert [persona["id"] for persona in por_telefono.json()] == [creada["id"]]
    assert [persona["id"] for persona in por_parametro.json()] == [creada["id"]]


def test_busqueda_por_nombre_de_mascota(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    creada = _crear(
        crear_persona_api,
        duenio,
        persona_payload,
        nombre="Ana",
        apellido="Perez",
        dni="30111222",
        telefono="11 4444-5555",
    )
    _crear(
        crear_persona_api,
        duenio,
        persona_payload,
        nombre="Beto",
        apellido="Gomez",
        dni="30999888",
        telefono="11 6666-7777",
    )
    paciente = client.post(
        "/api/pacientes",
        json={
            "nombre": "Firulais",
            "especie_id": especie_perro,
            "titular_persona_id": creada["id"],
        },
        headers=auth(duenio),
    )
    assert paciente.status_code == 201

    respuesta = client.get("/api/personas?q=Firulais", headers=auth(duenio))

    assert respuesta.status_code == 200
    assert [persona["id"] for persona in respuesta.json()] == [creada["id"]]


def test_paginacion_estable(
    client: TestClient, auth, duenio, crear_persona_api, persona_payload
) -> None:
    for indice, nombre in enumerate(("Ana", "Beto", "Carla"), start=1):
        _crear(
            crear_persona_api,
            duenio,
            persona_payload,
            nombre=nombre,
            apellido="Gomez",
            dni=f"3000000{indice}",
            telefono=f"11 4444-000{indice}",
        )

    pagina_1 = client.get(
        "/api/personas?q=Gomez&limit=1&offset=0", headers=auth(duenio)
    )
    pagina_2 = client.get(
        "/api/personas?q=Gomez&limit=1&offset=1", headers=auth(duenio)
    )
    pagina_3 = client.get(
        "/api/personas?q=Gomez&limit=1&offset=2", headers=auth(duenio)
    )
    pagina_4 = client.get(
        "/api/personas?q=Gomez&limit=1&offset=3", headers=auth(duenio)
    )

    assert [pagina.json()[0]["nombre"] for pagina in (pagina_1, pagina_2, pagina_3)] == [
        "Ana",
        "Beto",
        "Carla",
    ]
    assert pagina_4.json() == []


def test_busqueda_de_pacientes_por_nombre_y_titular(
    client: TestClient,
    auth,
    duenio,
    veterinario,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    titular = _crear(
        crear_persona_api,
        duenio,
        persona_payload,
        nombre="Ana",
        apellido="Perez",
        dni="30111222",
        telefono="11 4444-5555",
    )
    for nombre in ("Firulais", "Michi"):
        creado = client.post(
            "/api/pacientes",
            json={
                "nombre": nombre,
                "especie_id": especie_perro,
                "titular_persona_id": titular["id"],
            },
            headers=auth(duenio),
        )
        assert creado.status_code == 201

    por_nombre = client.get("/api/pacientes?q=Firu", headers=auth(veterinario))
    por_titular = client.get("/api/pacientes?q=Perez", headers=auth(veterinario))
    pagina_1 = client.get("/api/pacientes?limit=1&offset=0", headers=auth(duenio))
    pagina_2 = client.get("/api/pacientes?limit=1&offset=1", headers=auth(duenio))
    pagina_3 = client.get("/api/pacientes?limit=1&offset=2", headers=auth(duenio))

    assert [paciente["nombre"] for paciente in por_nombre.json()] == ["Firulais"]
    assert [paciente["nombre"] for paciente in por_titular.json()] == [
        "Firulais",
        "Michi",
    ]
    assert [p.json()[0]["nombre"] for p in (pagina_1, pagina_2)] == [
        "Firulais",
        "Michi",
    ]
    assert pagina_3.json() == []
