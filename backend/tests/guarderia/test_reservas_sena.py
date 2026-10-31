from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.modules.identidad.permisos import Rol


def _reserva_payload(tutor_persona_id: int, paciente_id: int) -> dict[str, object]:
    fecha = date.today() + timedelta(days=2)
    return {
        "tutor_persona_id": tutor_persona_id,
        "paciente_ids": [paciente_id],
        "desde_fecha": fecha.isoformat(),
        "desde_franja": "DIA",
        "hasta_fecha": fecha.isoformat(),
        "hasta_franja": "DIA",
        "cuidados_extras": [
            {"paciente_id": paciente_id, "cuidados_extras": False}
        ],
        "total_centavos": 7000000,
    }


def _crear_reserva(client, headers, tutor_persona_id: int, paciente_id: int):
    return client.post(
        "/api/guarderia/reservas",
        json=_reserva_payload(tutor_persona_id, paciente_id),
        headers={**headers, "Idempotency-Key": "reserva-sena-key"},
    )


def test_sena_confirma_y_deja_pago_y_saldo_en_cobros(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    creada = _crear_reserva(
        client,
        headers,
        datos.tutor_persona_id,
        datos.paciente_ids[0],
    )
    reserva_id = creada.json()["id"]

    respuesta = client.post(
        f"/api/guarderia/reservas/{reserva_id}/sena",
        json={"monto_centavos": 500000, "medio": "EFECTIVO"},
        headers={**headers, "Idempotency-Key": "pago-sena-key"},
    )
    cuenta = client.get(
        f"/api/personas/{datos.tutor_persona_id}/cuenta",
        headers=headers,
    )
    cargo = cuenta.json()["cargos"][0]

    assert creada.status_code == 201
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "CONFIRMADA"
    assert cargo["cargo"]["total_pagado"] == 500000
    assert cargo["cargo"]["saldo"] == 6500000
    assert len(cargo["pagos"]) == 1
    assert cargo["pagos"][0]["es_sena"] is True


@pytest.mark.parametrize("monto_centavos", [100000, 5000000])
def test_sena_de_monto_libre_confirma(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
    monto_centavos: int,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    creada = _crear_reserva(
        client,
        headers,
        datos.tutor_persona_id,
        datos.paciente_ids[0],
    )

    respuesta = client.post(
        f"/api/guarderia/reservas/{creada.json()['id']}/sena",
        json={"monto_centavos": monto_centavos, "medio": "TRANSFERENCIA"},
        headers={**headers, "Idempotency-Key": f"sena-libre-{monto_centavos}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "CONFIRMADA"


@pytest.mark.parametrize(
    ("monto_centavos", "medio"),
    [(0, "EFECTIVO"), (-1, "EFECTIVO"), (100000, "INEXISTENTE")],
)
def test_sena_rechaza_monto_invalido_o_medio_inexistente(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
    monto_centavos: int,
    medio: str,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    creada = _crear_reserva(
        client,
        headers,
        datos.tutor_persona_id,
        datos.paciente_ids[0],
    )

    respuesta = client.post(
        f"/api/guarderia/reservas/{creada.json()['id']}/sena",
        json={"monto_centavos": monto_centavos, "medio": medio},
        headers={**headers, "Idempotency-Key": "sena-invalida"},
    )

    assert respuesta.status_code == 422
    assert creada.json()["estado"] == "PENDIENTE_SENA"


def test_reintento_de_sena_con_la_misma_clave_no_duplica_el_pago(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    creada = _crear_reserva(
        client,
        headers,
        datos.tutor_persona_id,
        datos.paciente_ids[0],
    )
    ruta = f"/api/guarderia/reservas/{creada.json()['id']}/sena"
    pago_headers = {**headers, "Idempotency-Key": "sena-reintento"}
    cuerpo = {"monto_centavos": 100000, "medio": "EFECTIVO"}

    primera = client.post(ruta, json=cuerpo, headers=pago_headers)
    segunda = client.post(ruta, json=cuerpo, headers=pago_headers)
    cuenta = client.get(
        f"/api/personas/{datos.tutor_persona_id}/cuenta",
        headers=headers,
    )

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert len(cuenta.json()["cargos"][0]["pagos"]) == 1


def test_sena_exige_clave_idempotente(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    creada = _crear_reserva(
        client,
        headers,
        datos.tutor_persona_id,
        datos.paciente_ids[0],
    )

    respuesta = client.post(
        f"/api/guarderia/reservas/{creada.json()['id']}/sena",
        json={"monto_centavos": 100000, "medio": "EFECTIVO"},
        headers=headers,
    )

    assert respuesta.status_code == 422
