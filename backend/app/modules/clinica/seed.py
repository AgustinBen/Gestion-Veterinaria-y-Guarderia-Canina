"""Parámetros iniciales configurables del módulo clínica."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import parametros

DIAS_AVISO_VACUNA_INICIAL = 30


def sembrar_parametros(db: Session) -> None:
    parametros.registrar_parametro(
        db,
        "clinica.dias_aviso_vacuna",
        DIAS_AVISO_VACUNA_INICIAL,
        "int",
        modulo="clinica",
        descripcion="Días de aviso previos a la próxima dosis de una vacuna",
    )
