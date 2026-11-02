"""Schemas de la historia clínica y la libreta de vacunas."""

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.clinica.models import (
    EstadoTurno,
    FranjaTurnoPersonal,
    MedioEventoExterno,
    OrigenAtencion,
    TipoAtencion,
    TipoEstudio,
    TipoEventoExterno,
    TipoTurnoMedico,
)


class HorarioAtencionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dia_semana: int = Field(ge=0, le=6)
    hora_desde: time
    hora_hasta: time

    @model_validator(mode="after")
    def validar_rango_local(self) -> HorarioAtencionIn:
        if self.hora_desde.tzinfo is not None or self.hora_hasta.tzinfo is not None:
            raise ValueError("El horario debe usar la hora local sin zona horaria")
        if self.hora_desde >= self.hora_hasta:
            raise ValueError("La hora desde debe ser menor que la hora hasta")
        return self


class HorarioAtencionOut(HorarioAtencionIn):
    id: int


class TurnoPersonalDefIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turno: FranjaTurnoPersonal
    hora_desde: time
    hora_hasta: time

    @model_validator(mode="after")
    def validar_horas_locales(self) -> TurnoPersonalDefIn:
        if self.hora_desde.tzinfo is not None or self.hora_hasta.tzinfo is not None:
            raise ValueError("La definición debe usar la hora local sin zona horaria")
        if self.hora_desde == self.hora_hasta:
            raise ValueError("El inicio y el fin del turno deben ser distintos")
        return self


class TurnosPersonalDefinicionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turnos: list[TurnoPersonalDefIn]

    @model_validator(mode="after")
    def validar_unicidad(self) -> TurnosPersonalDefinicionIn:
        nombres = [turno.turno for turno in self.turnos]
        if len(nombres) != len(set(nombres)):
            raise ValueError("No se puede repetir la definición de un turno")
        if any(turno.hora_desde == turno.hora_hasta for turno in self.turnos):
            raise ValueError("El inicio y el fin del turno deben ser distintos")
        return self


class TurnoPersonalDefOut(TurnoPersonalDefIn):
    id: int


class TurnosPersonalDefinicionOut(BaseModel):
    turnos: list[TurnoPersonalDefOut]


class TurnoPersonalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empleado_id: int = Field(gt=0)
    fecha: date
    turno: FranjaTurnoPersonal


class TurnoPersonalOut(TurnoPersonalIn):
    empleado_nombre: str


class TurnoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paciente_id: int = Field(gt=0)
    tipo: TipoTurnoMedico
    veterinario_empleado_id: int = Field(gt=0)
    inicio: datetime
    fin: datetime
    motivo: str | None = None
    externo_empleado_id: int | None = Field(default=None, gt=0)
    # Monto a cobrar al dueño, en centavos. Opcional: sin monto no se crea cargo.
    monto_centavos: int | None = Field(default=None, gt=0, strict=True)

    @model_validator(mode="after")
    def validar_horas_locales(self) -> TurnoCrear:
        if self.inicio.tzinfo is not None or self.fin.tzinfo is not None:
            raise ValueError("Los turnos deben usar la hora local sin zona horaria")
        if self.inicio >= self.fin:
            raise ValueError("El fin debe ser posterior al inicio")
        if self.tipo == TipoTurnoMedico.CIRUGIA and self.externo_empleado_id is None:
            raise ValueError("La cirugía requiere un veterinario externo")
        if self.tipo != TipoTurnoMedico.CIRUGIA and self.externo_empleado_id is not None:
            raise ValueError("Solo una cirugía puede indicar un veterinario externo")
        return self


class TurnoReprogramar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: datetime | None = None
    fin: datetime | None = None
    veterinario_empleado_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validar_reprogramacion(self) -> TurnoReprogramar:
        if not self.model_fields_set or all(
            getattr(self, campo) is None for campo in self.model_fields_set
        ):
            raise ValueError("Debe indicar al menos un campo para reprogramar")
        if any(getattr(self, campo) is None for campo in self.model_fields_set):
            raise ValueError("Los campos enviados para reprogramar no pueden ser nulos")
        if self.inicio is not None and self.inicio.tzinfo is not None:
            raise ValueError("Los turnos deben usar la hora local sin zona horaria")
        if self.fin is not None and self.fin.tzinfo is not None:
            raise ValueError("Los turnos deben usar la hora local sin zona horaria")
        if self.inicio is not None and self.fin is not None and self.inicio >= self.fin:
            raise ValueError("El fin debe ser posterior al inicio")
        return self


class TurnoCancelar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=1)


class TurnoAtendido(BaseModel):
    model_config = ConfigDict(extra="forbid")

    atencion_id: int | None = Field(default=None, gt=0)


class TurnoOut(BaseModel):
    id: int
    paciente_id: int
    tipo: TipoTurnoMedico
    veterinario_empleado_id: int
    inicio: datetime
    fin: datetime
    estado: EstadoTurno
    motivo: str | None
    atencion_id: int | None
    externo_actual_id: int | None
    cargo_id: int | None = None
    created_by: int
    created_at: datetime


class TurnoAtendidoOut(TurnoOut):
    gasto_registrado: bool = False


class ExternoContactadoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medio: MedioEventoExterno
    nota: str | None = None


class ExternoConfirmarIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    costo_acordado_centavos: int = Field(gt=0, strict=True)


class ExternoRechazarIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=1)


class ExternoReemplazarIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    externo_empleado_id: int = Field(gt=0)


class EventoExternoOut(BaseModel):
    id: int
    turno_id: int
    tipo: TipoEventoExterno
    externo_empleado_id: int
    externo_nombre: str | None
    medio: MedioEventoExterno | None
    nota: str | None
    costo_acordado_centavos: int | None
    costo_registrado: bool
    usuario_id: int
    created_at: datetime


class EmpleadoTraspaso(BaseModel):
    empleado_id: int
    nombre: str


class VentanaTraspasoOut(BaseModel):
    inicio: datetime
    fin: datetime
    turno_sale: FranjaTurnoPersonal
    turno_entra: FranjaTurnoPersonal
    empleados_salen: list[EmpleadoTraspaso]
    empleados_entran: list[EmpleadoTraspaso]


class AgendaDiaOut(BaseModel):
    fecha: date
    horarios_atencion: list[HorarioAtencionOut]
    turnos: list[TurnoOut]
    turnos_personal: list[TurnoPersonalOut]
    ventanas_traspaso: list[VentanaTraspasoOut]


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


class EstudioCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: TipoEstudio
    fecha: date
    descripcion: str = Field(min_length=1)
    realizado_por_empleado_id: int = Field(gt=0, strict=True)
    costo_centavos: int | None = Field(default=None, gt=0, strict=True)


class AdjuntoResumen(BaseModel):
    id: int
    nombre_original: str
    tipo_mime: str
    tamano_bytes: int
    sha256: str
    created_by: int
    created_at: datetime


class EstudioResumen(BaseModel):
    id: int
    paciente_id: int
    atencion_id: int | None
    tipo: TipoEstudio
    fecha: date
    descripcion: str
    realizado_por_empleado_id: int
    cargo_id: int | None
    created_by: int
    created_at: datetime
    adjuntos: list[AdjuntoResumen] = Field(default_factory=list)


class PacienteClinicaResumen(BaseModel):
    """Mascota para listados de historia clínica filtrados por atención."""

    id: int
    nombre: str
    especie_id: int
    especie_nombre: str
    raza_id: int | None
    raza_nombre: str | None
    activo: bool
