"""Schemas de consultas de cupo de guardería."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.guarderia.franjas import Franja


class Disponibilidad(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: date
    franja: Franja
    cupo_maximo: int
    plazas_emergencia: int
    habilitadas: int
    publico: int
    ocupado: int
    disponible: int


class FranjaSinLugar(BaseModel):
    fecha: date
    franja: Franja
    necesita: int
    disponible: int


class OcupacionExistente(BaseModel):
    paciente_id: int
    fecha: date
    franja: Franja


class ResultadoCupo(BaseModel):
    aprobado: bool
    codigo: Literal["DISPONIBLE", "SIN_CUPO", "YA_RESERVADO"]
    franjas_sin_lugar: list[FranjaSinLugar]
    ocupaciones_existentes: list[OcupacionExistente]
