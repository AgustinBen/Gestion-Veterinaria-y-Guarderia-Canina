"""Parámetros iniciales configurables del módulo clínica."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import parametros

DIAS_AVISO_VACUNA_INICIAL = 30
MINUTOS_TRASPASO_INICIAL = 30
TRASPASO_BLOQUEA_TURNOS_INICIAL = False
DURACION_TURNO_SUGERIDA_MIN_INICIAL = 30


def sembrar_parametros(db: Session) -> None:
    parametros.registrar_parametro(
        db,
        "clinica.dias_aviso_vacuna",
        DIAS_AVISO_VACUNA_INICIAL,
        "int",
        modulo="clinica",
        descripcion="Días de aviso previos a la próxima dosis de una vacuna",
    )
    parametros.registrar_parametro(
        db,
        "clinica.minutos_traspaso",
        MINUTOS_TRASPASO_INICIAL,
        "int",
        modulo="clinica",
        descripcion="Duración en minutos de cada ventana de traspaso",
    )
    parametros.registrar_parametro(
        db,
        "clinica.traspaso_bloquea_turnos",
        TRASPASO_BLOQUEA_TURNOS_INICIAL,
        "bool",
        modulo="clinica",
        descripcion="Indica si las ventanas de traspaso bloquean turnos médicos",
    )
    parametros.registrar_parametro(
        db,
        "clinica.duracion_turno_sugerida_min",
        DURACION_TURNO_SUGERIDA_MIN_INICIAL,
        "int",
        modulo="clinica",
        descripcion="Duración sugerida para un turno médico",
    )
