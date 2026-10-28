"""Tests de duplicados: DNI bloquea, teléfono y nombre avisan (RN-02, RN-06)."""

from __future__ import annotations

from decimal import Decimal

from app.core import parametros
from app.modules.padron import normalizacion, repository, service


def test_telefono_repetido_en_otro_formato_avisa(
    crear_persona_api, duenio, persona_payload
) -> None:
    primera = crear_persona_api(
        duenio,
        persona_payload(
            nombre="Ana",
            apellido="Perez",
            dni="30111222",
            telefonos=["1155551234"],
        ),
    )
    assert primera.status_code == 201

    repetida = crear_persona_api(
        duenio,
        persona_payload(
            nombre="Beto",
            apellido="Gomez",
            dni="30999888",
            telefonos=["+54 9 11 5555-1234"],
        ),
    )

    assert repetida.status_code == 409
    detalle = repetida.json()["detail"]
    assert detalle["codigo"] == "POSIBLE_DUPLICADO"
    assert detalle["coincidencias"][0]["persona"]["id"] == primera.json()["id"]
    assert detalle["coincidencias"][0]["motivo"] == "TELEFONO"


def test_confirmar_duplicado_crea_y_registra_usuario(
    db_session, crear_persona_api, duenio, persona_payload
) -> None:
    primera = crear_persona_api(
        duenio,
        persona_payload(
            nombre="Ana",
            apellido="Perez",
            dni="30111222",
            telefonos=["1155551234"],
        ),
    )
    assert primera.status_code == 201
    primera_id = primera.json()["id"]

    payload = persona_payload(
        nombre="Beto",
        apellido="Gomez",
        dni="30999888",
        telefonos=["+54 9 11 5555-1234"],
        confirmar_duplicado=True,
        persona_coincidente_id=primera_id,
    )
    confirmada = crear_persona_api(duenio, payload)

    assert confirmada.status_code == 201
    assert confirmada.json()["duplicado_confirmado"] is True
    persona = repository.obtener_persona(db_session, confirmada.json()["id"])
    assert persona is not None
    assert persona.duplicado_confirmado is True
    assert persona.creado_por == duenio.id
    assert persona.creado_en is not None
    assert len(service.buscar_personas(db_session, limite=100)) == 2


def test_nombre_parecido_avisa(
    crear_persona_api, duenio, persona_payload
) -> None:
    primera = crear_persona_api(
        duenio,
        persona_payload(
            nombre="María",
            apellido="Gómez",
            dni="30111222",
            telefonos=["11 4444-5555"],
        ),
    )
    assert primera.status_code == 201

    parecida = crear_persona_api(
        duenio,
        persona_payload(
            nombre="Maria",
            apellido="Gomez",
            dni="30999888",
            telefonos=["11 6666-7777"],
        ),
    )

    assert parecida.status_code == 409
    detalle = parecida.json()["detail"]
    assert detalle["codigo"] == "POSIBLE_DUPLICADO"
    assert detalle["coincidencias"][0]["motivo"] == "NOMBRE"
    assert detalle["coincidencias"][0]["persona"]["id"] == primera.json()["id"]


def test_nombre_distinto_no_avisa(
    crear_persona_api, duenio, persona_payload
) -> None:
    primera = crear_persona_api(
        duenio,
        persona_payload(
            nombre="María",
            apellido="Gómez",
            dni="30111222",
            telefonos=["11 4444-5555"],
        ),
    )
    assert primera.status_code == 201

    distinta = crear_persona_api(
        duenio,
        persona_payload(
            nombre="Marcos",
            apellido="Pérez",
            dni="30999888",
            telefonos=["11 6666-7777"],
        ),
    )

    assert distinta.status_code == 201


def test_umbral_configurable_cambia_el_aviso(
    db_session, crear_persona_api, duenio, persona_payload
) -> None:
    primera = crear_persona_api(
        duenio,
        persona_payload(
            nombre="María",
            apellido="Gómez",
            dni="30111222",
            telefonos=["11 4444-5555"],
        ),
    )
    assert primera.status_code == 201

    payload = persona_payload(
        nombre="María",
        apellido="Gome",
        dni="30999888",
        telefonos=["11 6666-7777"],
    )

    con_umbral_inicial = crear_persona_api(duenio, payload)
    assert con_umbral_inicial.status_code == 409
    assert con_umbral_inicial.json()["detail"]["codigo"] == "POSIBLE_DUPLICADO"

    parametros.set_param(
        db_session,
        normalizacion.CLAVE_UMBRAL_NOMBRE_PARECIDO,
        Decimal("0.99"),
        "decimal",
    )

    con_umbral_alto = crear_persona_api(duenio, payload)
    assert con_umbral_alto.status_code == 201
