"""Schemas de la historia clínica y la libreta de vacunas."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.clinica.models import OrigenAtencion, TipoAtencion


class VacunaNueva(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre_vacuna: str = Field(min_length=1, max_length=100)
    lote: str | None = Field(default=None, max_length=100)
    fecha_aplicacion: date
    proxima_dosis: date | None = None


class AtencionCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: TipoAtencion
    fecha_hora: datetime | None = None
    veterinario_empleado_id: int | None = Field(default=None, gt=0)
    motivo: str | None = None
    diagnostico: str | None = None
    tratamiento: str | None = None
    observaciones: str | None = None
    cirujano_externo_id: int | None = Field(default=None, gt=0)
    cargo_id: int | None = Field(default=None, gt=0)
    vacuna: VacunaNueva | None = None

    @model_validator(mode="after")
    def validar_datos_segun_tipo(self) -> AtencionCrear:
        if self.tipo == TipoAtencion.CIRUGIA and self.cirujano_externo_id is None:
            raise ValueError("La cirugía requiere un cirujano externo")
        if self.tipo != TipoAtencion.CIRUGIA and self.cirujano_externo_id is not None:
            raise ValueError("Solo una cirugía puede indicar cirujano externo")
        if self.tipo == TipoAtencion.VACUNA and self.vacuna is None:
            raise ValueError("La atención de tipo VACUNA requiere los datos de vacuna")
        if self.tipo != TipoAtencion.VACUNA and self.vacuna is not None:
            raise ValueError("Solo una atención de tipo VACUNA puede incluir vacuna")
        return self


class AtencionResumen(BaseModel):
    id: int
    paciente_id: int
    tipo: TipoAtencion
    fecha_hora: datetime
    veterinario_empleado_id: int
    veterinario_nombre: str | None
    motivo: str | None
    diagnostico: str | None
    tratamiento: str | None
    observaciones: str | None
    cirujano_externo_id: int | None
    cirujano_externo_nombre: str | None
    cargo_id: int | None
    origen: OrigenAtencion
    texto_original: str | None
    rectifica_a_id: int | None
    rectificada: bool


class VacunaAplicadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    atencion_id: int
    nombre_vacuna: str
    lote: str | None
    fecha_aplicacion: date
    proxima_dosis: date | None


class AtencionDetalle(AtencionResumen):
    created_by: int
    created_at: datetime
    vacuna: VacunaAplicadaOut | None


class EstadoVacuna(str, Enum):
    VIGENTE = "VIGENTE"
    POR_VENCER = "POR_VENCER"
    VENCIDA = "VENCIDA"


class LibretaVacunasItem(BaseModel):
    atencion_id: int
    nombre_vacuna: str
    lote: str | None
    fecha_aplicacion: date
    proxima_dosis: date | None
    estado: EstadoVacuna
