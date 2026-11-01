from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select

from app.modules.cobros import service as cobros_service
from app.modules.guarderia.models import CancelacionReserva, Ocupacion
from app.modules.identidad.permisos import Rol


def _crear_reserva(client, headers, tutor_id: int, paciente_ids: list[int]) -> dict:
    fecha = date.today() + timedelta(days=2)
    solicitud = {
        "tutor_persona_id": tutor_id,
        "paciente_ids": paciente_ids,
        "desde_fecha": fecha.isoformat(),
        "desde_franja": "DIA",
        "hasta_fecha": fecha.isoformat(),
        "hasta_franja": "NOCHE",
        "cuidados_extras": [
            {"paciente_id": paciente_id, "cuidados_extras": False}
            for paciente_id in paciente_ids
        ],
        "total_centavos": 300000,
    }
    respuesta = client.post(
        "/api/guarderia/reservas",
        json=solicitud,
        headers={**headers, "Idempotency-Key": "crear-reserva-cancelable"},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def test_personal_cancela_y_cierra_saldo_sin_revertir_pagos(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    duenio = crear_usuario(Rol.DUENIO)
    personal = crear_usuario(Rol.PERSONAL)
    reserva = _crear_reserva(
        client,
        token_guarderia(duenio),
        datos.tutor_persona_id,
        datos.paciente_ids,
    )
    reserva_id = reserva["id"]
    cargo_id = reserva["cargo_id"]
    respuesta_sena = client.post(
        f"/api/guarderia/reservas/{reserva_id}/sena",
        json={"monto_centavos": 20000, "medio": "TRANSFERENCIA"},
        headers={
            **token_guarderia(duenio),
            "Idempotency-Key": "registrar-sena-cancelable",
        },
    )
    assert respuesta_sena.status_code == 200
    cobros_service.registrar_pago(
        db_session,
        cargo_id=cargo_id,
        monto_centavos=10000,
        medio="TRANSFERENCIA",
        usuario_id=duenio.id,
        clave_idempotencia="pago-parcial-cancelable",
    )

    headers = {
        **token_guarderia(personal),
        "Idempotency-Key": "cancelar-reserva-cancelable",
    }
    cancelada = client.post(
        f"/api/guarderia/reservas/{reserva_id}/cancelar",
        headers=headers,
    )
    repetida = client.post(
        f"/api/guarderia/reservas/{reserva_id}/cancelar",
        headers=headers,
    )

    assert cancelada.status_code == 200
    assert cancelada.json()["estado"] == "CANCELADA"
    assert repetida.status_code == 200
    assert db_session.scalar(
        select(func.count(Ocupacion.id)).where(
            Ocupacion.reserva_id == reserva_id
        )
    ) == 0
    assert db_session.get(CancelacionReserva, reserva_id).usuario_id == personal.id

    cargo = cobros_service.obtener_cargo_detalle(db_session, cargo_id)
    assert cargo.total_pagado == 30000
    assert cargo.total_vigente == 30000
    assert cargo.saldo == 0
    ajustes = cobros_service.listar_ajustes(db_session, cargo_id)
    assert len(ajustes) == 1
    assert ajustes[0].precio_nuevo == 30000


def test_cancelar_reserva_sin_pagos_cierra_el_cargo_en_cero(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    reserva = _crear_reserva(
        client,
        token_guarderia(usuario),
        datos.tutor_persona_id,
        datos.paciente_ids,
    )

    respuesta = client.post(
        f"/api/guarderia/reservas/{reserva['id']}/cancelar",
        headers={
            **token_guarderia(usuario),
            "Idempotency-Key": "cancelar-sin-pagos",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "CANCELADA"
    cargo = cobros_service.obtener_cargo_detalle(db_session, reserva["cargo_id"])
    assert cargo.total_vigente == 0
    assert cargo.total_pagado == 0
    assert cargo.saldo == 0
    ajustes = cobros_service.listar_ajustes(db_session, reserva["cargo_id"])
    assert len(ajustes) == 1
    assert ajustes[0].precio_nuevo == 0


def test_solo_duenio_o_personal_pueden_cancelar_reserva(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    duenio = crear_usuario(Rol.DUENIO)
    reserva = _crear_reserva(
        client,
        token_guarderia(duenio),
        datos.tutor_persona_id,
        datos.paciente_ids,
    )
    veterinario = crear_usuario(Rol.VETERINARIO)

    respuesta = client.post(
        f"/api/guarderia/reservas/{reserva['id']}/cancelar",
        headers={
            **token_guarderia(veterinario),
            "Idempotency-Key": "cancelar-como-veterinario",
        },
    )

    assert respuesta.status_code == 403
