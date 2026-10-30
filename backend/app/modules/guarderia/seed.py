"""Parámetros iniciales configurables del módulo guardería."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import parametros

CUPO_MAXIMO_INICIAL = 10
PLAZAS_EMERGENCIA_INICIAL = 1
RESERVA_MAX_MESES_INICIAL = 4
DESCUENTO_MULTIMASCOTA_PCT_INICIAL = Decimal("20")


def sembrar_parametros(db: Session) -> None:
    parametros.registrar_parametro(
        db,
        "guarderia.cupo_maximo",
        CUPO_MAXIMO_INICIAL,
        "int",
        modulo="guarderia",
        descripcion="Cupo máximo por fecha y franja (rango de uso: 8 a 10)",
    )
    parametros.registrar_parametro(
        db,
        "guarderia.plazas_emergencia",
        PLAZAS_EMERGENCIA_INICIAL,
        "int",
        modulo="guarderia",
        descripcion="Plazas reservadas para emergencias por franja",
    )
    parametros.registrar_parametro(
        db,
        "guarderia.reserva_max_meses",
        RESERVA_MAX_MESES_INICIAL,
        "int",
        modulo="guarderia",
        descripcion="Anticipación máxima de reservas, en meses",
    )
    parametros.registrar_parametro(
        db,
        "guarderia.descuento_multimascota_pct",
        DESCUENTO_MULTIMASCOTA_PCT_INICIAL,
        "decimal",
        modulo="guarderia",
        descripcion="Descuento porcentual por reserva de varias mascotas",
    )
