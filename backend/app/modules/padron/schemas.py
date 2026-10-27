"""Schemas de entrada y salida del módulo padrón."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.padron.models import TipoEmpleado


class DomicilioNuevo(BaseModel):
    """Domicilio opcional de una persona."""

    model_config = ConfigDict(extra="forbid")

    calle: str | None = None
    numero: int | None = None
    piso: str | None = None
    departamento: str | None = None
    localidad: str | None = None
    codigo_postal: str | None = None
    referencia: str | None = None


class DomicilioOut(BaseModel):
    """Domicilio tal como se devuelve en la ficha."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    calle: str | None
    numero: int | None
    piso: str | None
    departamento: str | None
    localidad: str | None
    codigo_postal: str | None
    referencia: str | None


class PersonaNueva(BaseModel):
    """Alta de una persona. El DNI lo exige el router (RN-01)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    apellido: str
    dni: str | None = None
    domicilio: DomicilioNuevo | None = None
    telefonos: list[str] = Field(default_factory=list)
    confirmar_duplicado: bool = False
    persona_coincidente_id: int | None = None


class PersonaActualizar(BaseModel):
    """Cambios parciales de una persona. Lo omitido no se toca."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    apellido: str | None = None
    dni: str | None = None
    domicilio: DomicilioNuevo | None = None
    telefonos: list[str] | None = None
    confirmar_duplicado: bool = False
    persona_coincidente_id: int | None = None


class TelefonosUpdate(BaseModel):
    """Reemplazo completo de la lista de teléfonos de una persona."""

    model_config = ConfigDict(extra="forbid")

    telefonos: list[str] = Field(default_factory=list)
    confirmar_duplicado: bool = False
    persona_coincidente_id: int | None = None


class PacienteResumen(BaseModel):
    """Mascota en listados y resúmenes."""

    id: int
    nombre: str
    especie_id: int
    especie_nombre: str
    raza_id: int | None
    raza_nombre: str | None
    activo: bool


class TitularVigente(BaseModel):
    """Titular vigente de una mascota."""

    persona_id: int
    nombre: str
    apellido: str
    tipo: str
    principal: bool
    desde: date


class PersonaResumen(BaseModel):
    """Persona en listados, búsquedas y avisos de duplicados."""

    id: int
    nombre: str
    apellido: str
    dni: str | None
    dni_pendiente: bool
    telefonos: list[str]


class PersonaDetalle(BaseModel):
    """Ficha completa de una persona."""

    id: int
    nombre: str
    apellido: str
    dni: str | None
    dni_pendiente: bool
    domicilio: DomicilioOut | None
    telefonos: list[str]
    creado_en: datetime
    duplicado_confirmado: bool
    mascotas: list[PacienteResumen]


class PacienteNuevo(BaseModel):
    """Alta de una mascota. La especie es obligatoria (RN-05)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    especie_id: int
    raza_id: int | None = None
    tamanio_id: int | None = None
    peso_kg: Decimal | None = None
    fecha_nacimiento_aprox: date | None = None
    castrado: bool | None = None
    titular_persona_id: int


class PacienteActualizar(BaseModel):
    """Cambios parciales de una mascota. La edad nunca se acepta."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    especie_id: int | None = None
    raza_id: int | None = None
    tamanio_id: int | None = None
    peso_kg: Decimal | None = None
    fecha_nacimiento_aprox: date | None = None
    castrado: bool | None = None
    activo: bool | None = None


class PacienteDetalle(BaseModel):
    """Ficha de una mascota con la edad calculada y sin factor de cupo."""

    id: int
    nombre: str
    especie_id: int
    especie_nombre: str
    raza_id: int | None
    raza_nombre: str | None
    tamanio_id: int | None
    tamanio_nombre: str | None
    peso_kg: Decimal | None
    fecha_nacimiento_aprox: date | None
    castrado: bool | None
    activo: bool
    edad_anios: int | None
    edad_meses: int | None


class EmpleadoNuevo(BaseModel):
    """Alta de un empleado junto con su persona."""

    model_config = ConfigDict(extra="forbid")

    persona: PersonaNueva
    tipo: TipoEmpleado = TipoEmpleado.INTERNO
    es_veterinario: bool = False
    especialidad: str | None = None
    email: str | None = None
    activo: bool = True


class EmpleadoActualizar(BaseModel):
    """Cambios parciales de la fila empleado."""

    model_config = ConfigDict(extra="forbid")

    tipo: TipoEmpleado | None = None
    es_veterinario: bool | None = None
    especialidad: str | None = None
    email: str | None = None
    activo: bool | None = None


class EmpleadoDetalle(BaseModel):
    """Empleado con los datos de su persona."""

    persona_id: int
    nombre: str
    apellido: str
    dni: str | None
    dni_pendiente: bool
    telefonos: list[str]
    tipo: TipoEmpleado
    es_veterinario: bool
    especialidad: str | None
    email: str | None
    activo: bool


class EspecieOut(BaseModel):
    """Especie del catálogo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class RazaOut(BaseModel):
    """Raza del catálogo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    especie_id: int


class RazaNueva(BaseModel):
    """Alta rápida de una raza desde el formulario de la mascota."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    especie_id: int


class TamanioOut(BaseModel):
    """Tamaño descriptivo de la mascota (sin factor de cupo)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class CoincidenciaOut(BaseModel):
    """Coincidencia que exige confirmación explícita (RN-06)."""

    persona: PersonaResumen
    motivo: str
    mascotas: list[str]
