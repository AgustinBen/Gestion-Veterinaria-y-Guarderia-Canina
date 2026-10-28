"""Tests de alta, ficha y edición de personas (RN-01, RN-02, RN-08, RN-09)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.modules.padron import schemas, service


def test_crear_persona_normaliza_dni_y_telefono(
    crear_persona_api, duenio, persona_payload
) -> None:
    respuesta = crear_persona_api(
        duenio,
        persona_payload(dni="30.111.222", telefonos=["+54 9 11 4444-5555"]),
    )

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["dni"] == "30111222"
    assert datos["telefonos"] == ["1144445555"]
    assert datos["dni_pendiente"] is False


def test_persona_sin_apellido_422(
    crear_persona_api, duenio, persona_payload
) -> None:
    respuesta = crear_persona_api(duenio, persona_payload(apellido="   "))

    assert respuesta.status_code == 422


def test_persona_sin_dni_422(crear_persona_api, duenio, persona_payload) -> None:
    respuesta = crear_persona_api(duenio, persona_payload(dni=None))

    assert respuesta.status_code == 422


def test_persona_sin_telefono_422(
    crear_persona_api, duenio, persona_payload
) -> None:
    respuesta = crear_persona_api(duenio, persona_payload(telefonos=[]))

    assert respuesta.status_code == 422


def test_dni_repetido_bloquea_el_alta_aunque_se_confirme(
    crear_persona_api, duenio, persona_payload
) -> None:
    primera = crear_persona_api(duenio, persona_payload())
    assert primera.status_code == 201
    persona_id = primera.json()["id"]

    repetida = crear_persona_api(
        duenio,
        persona_payload(
            nombre="Otra",
            apellido="Persona",
            telefonos=["11 6666-7777"],
            confirmar_duplicado=True,
            persona_coincidente_id=persona_id,
        ),
    )

    assert repetida.status_code == 409
    detalle = repetida.json()["detail"]
    assert detalle["codigo"] == "DNI_DUPLICADO"
    assert detalle["persona"]["id"] == persona_id


def test_dni_repetido_bloquea_la_edicion(
    client: TestClient, auth, crear_persona_api, duenio, persona_payload
) -> None:
    primera = crear_persona_api(duenio, persona_payload())
    segunda = crear_persona_api(
        duenio,
        persona_payload(
            nombre="Beto",
            apellido="Gomez",
            dni="30999888",
            telefonos=["11 6666-7777"],
        ),
    )
    assert primera.status_code == 201
    assert segunda.status_code == 201
    segunda_id = segunda.json()["id"]

    respuesta = client.patch(
        f"/api/personas/{segunda_id}",
        json={
            "dni": "30111222",
            "confirmar_duplicado": True,
            "persona_coincidente_id": primera.json()["id"],
        },
        headers=auth(duenio),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "DNI_DUPLICADO"


def test_patch_persona_y_put_telefonos(
    client: TestClient, auth, crear_persona_api, duenio, persona_payload
) -> None:
    creada = crear_persona_api(duenio, persona_payload())
    assert creada.status_code == 201
    persona_id = creada.json()["id"]

    editada = client.patch(
        f"/api/personas/{persona_id}",
        json={
            "nombre": "Ana Maria",
            "domicilio": {"calle": "Av. Siempre Viva", "numero": 742, "localidad": "Springfield"},
        },
        headers=auth(duenio),
    )
    assert editada.status_code == 200
    assert editada.json()["nombre"] == "Ana Maria"
    assert editada.json()["domicilio"]["calle"] == "Av. Siempre Viva"

    telefonos = client.put(
        f"/api/personas/{persona_id}/telefonos",
        json={"telefonos": ["11 5555-6666", "+54 9 11 7777-8888"]},
        headers=auth(duenio),
    )
    assert telefonos.status_code == 200
    assert telefonos.json()["telefonos"] == ["1155556666", "1177778888"]


def test_domicilio_desde_pantalla_exige_calle_y_localidad(
    crear_persona_api, duenio, persona_payload
) -> None:
    sin_localidad = crear_persona_api(
        duenio,
        persona_payload(domicilio={"calle": "Av. Siempre Viva"}),
    )
    sin_calle = crear_persona_api(
        duenio,
        persona_payload(domicilio={"localidad": "Springfield"}),
    )

    assert sin_localidad.status_code == 422
    assert sin_calle.status_code == 422


def test_persona_migrada_sin_dni_marca_dni_pendiente(db_session) -> None:
    detalle = service.crear_persona(
        db_session,
        schemas.PersonaNueva(nombre="Sin", apellido="Dni", telefonos=[]),
        migrado=True,
    )

    assert detalle.dni is None
    assert detalle.dni_pendiente is True


def test_no_existe_funcion_ni_ruta_de_fusion() -> None:
    assert not any("fusion" in nombre.lower() for nombre in dir(service))
    rutas = app.openapi()["paths"]
    assert not any("fusion" in ruta.lower() for ruta in rutas)
