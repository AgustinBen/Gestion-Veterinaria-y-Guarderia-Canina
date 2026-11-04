"""T-66: el cargo expone el estado de la reserva de guardería vinculada."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core import parametros
from app.modules.cobros import service
from app.modules.guarderia import seed as guarderia_seed
from app.modules.guarderia import service as guarderia_service
from app.modules.guarderia.schemas import CuidadoExtraAnimal, ReservaCrear


@pytest.fixture(autouse=True)
def _cache_parametros_limpia() -> Generator[None, None, None]:
    parametros._limpiar_cache()
    yield
    parametros._limpiar_cache()


def _crear_reserva(db: Session, referencias, clave: str) -> tuple[int, int]:
    """Crea una reserva por el servicio de guardería y devuelve (reserva_id, cargo_id)."""
    guarderia_seed.sembrar_parametros(db)
    fecha = date.today() + timedelta(days=1)
    reserva, _ = guarderia_service.crear_reserva(
        db,
        ReservaCrear(
            tutor_persona_id=referencias.persona_id,
            paciente_ids=[referencias.paciente_id],
            desde_fecha=fecha,
            desde_franja="DIA",
            hasta_fecha=fecha,
            hasta_franja="NOCHE",
            cuidados_extras=[
                CuidadoExtraAnimal(
                    paciente_id=referencias.paciente_id,
                    cuidados_extras=False,
                )
            ],
            total_centavos=30000,
        ),
        clave_idempotencia=clave,
        usuario_id=referencias.usuario_id,
    )
    assert reserva.cargo_id is not None
    return reserva.id, reserva.cargo_id


def test_cargo_de_reserva_cancelada_expone_cancelada_y_conserva_pagos(
    db_session: Session,
    referencias_cobros,
) -> None:
    reserva_id, cargo_id = _crear_reserva(
        db_session, referencias_cobros, "reserva-a-cancelar"
    )
    service.registrar_pago(
        db_session,
        cargo_id=cargo_id,
        monto_centavos=5000,
        medio="EFECTIVO",
        es_sena=True,
        usuario_id=referencias_cobros.usuario_id,
    )
    guarderia_service.cancelar_reserva(
        db_session,
        reserva_id,
        clave_idempotencia="cancelacion-t66",
        usuario_id=referencias_cobros.usuario_id,
    )

    detalle = service.obtener_cargo_detalle(db_session, cargo_id)

    assert detalle.reserva_estado == "CANCELADA"
    assert detalle.total_pagado == 5000
    assert detalle.saldo == 0


def test_cargo_de_reserva_activa_no_expone_cancelada(
    db_session: Session,
    referencias_cobros,
) -> None:
    _, cargo_id = _crear_reserva(db_session, referencias_cobros, "reserva-activa")

    detalle = service.obtener_cargo_detalle(db_session, cargo_id)

    assert detalle.reserva_estado == "PENDIENTE_SENA"


def test_cargo_sin_reserva_no_expone_estado(
    db_session: Session,
    referencias_cobros,
) -> None:
    cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Consulta",
        total_centavos=10000,
        usuario_id=referencias_cobros.usuario_id,
    )
    huerfano = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Reserva de guardería #999",
        total_centavos=10000,
        referencia_tipo="RESERVA",
        referencia_id=999999,
        usuario_id=referencias_cobros.usuario_id,
    )

    assert service.obtener_cargo_detalle(db_session, cargo.id).reserva_estado is None
    assert service.obtener_cargo_detalle(db_session, huerfano.id).reserva_estado is None
