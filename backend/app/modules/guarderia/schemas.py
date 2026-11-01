"""Schemas para consultas de cupo y reservas de guardería."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import EstadoReserva


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


class HabilitacionEmergenciaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date
    franja: Franja
    motivo: str = Field(min_length=1, max_length=500)

    @field_validator("motivo")
    @classmethod
    def normalizar_motivo(cls, valor: str) -> str:
        motivo = valor.strip()
        if not motivo:
            raise ValueError("El motivo es obligatorio")
        return motivo


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


class CuidadoExtraAnimal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paciente_id: int = Field(gt=0, strict=True)
    cuidados_extras: bool
    tipo_cuidado: str | None = None

    @field_validator("tipo_cuidado")
    @classmethod
    def normalizar_tipo_cuidado(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        detalle = valor.strip()
        return detalle or None

    @model_validator(mode="after")
    def validar_tipo_cuidado(self) -> CuidadoExtraAnimal:
        if not self.cuidados_extras and self.tipo_cuidado is not None:
            raise ValueError("No puede indicar tipo de cuidado si cuidados_extras es falso")
        return self


class ReservaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tutor_persona_id: int = Field(gt=0, strict=True)
    paciente_ids: list[StrictInt] = Field(min_length=1)
    desde_fecha: date
    desde_franja: Franja
    hasta_fecha: date
    hasta_franja: Franja
    cuidados_extras: list[CuidadoExtraAnimal] = Field(min_length=1)
    total_centavos: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def validar_pacientes_y_cuidados(self) -> ReservaCrear:
        if len(set(self.paciente_ids)) != len(self.paciente_ids):
            raise ValueError("El pedido no puede repetir pacientes")
        if any(paciente_id <= 0 for paciente_id in self.paciente_ids):
            raise ValueError("Los pacientes deben tener identificadores positivos")
        ids_cuidados = [cuidado.paciente_id for cuidado in self.cuidados_extras]
        if len(set(ids_cuidados)) != len(ids_cuidados):
            raise ValueError("No se pueden repetir cuidados por paciente")
        if set(ids_cuidados) != set(self.paciente_ids):
            raise ValueError("Debe indicar cuidados_extras para cada paciente")
        return self


class ReservaSenaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monto_centavos: int = Field(gt=0, strict=True)
    medio: str = Field(min_length=1)


class ReservaPacienteOut(BaseModel):
    paciente_id: int
    cuidados_extras: bool
    tipo_cuidado: str | None


class ReservaOut(BaseModel):
    id: int
    tutor_persona_id: int
    desde_fecha: date
    desde_franja: Franja
    hasta_fecha: date
    hasta_franja: Franja
    estado: EstadoReserva
    cargo_id: int | None
    total_centavos: int | None
    sena_centavos: int
    pacientes: list[ReservaPacienteOut]
    created_at: datetime
