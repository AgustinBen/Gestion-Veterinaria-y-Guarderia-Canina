"""Schemas del módulo cobros."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MedioPagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    activo: bool


class CargoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona_id: int
    concepto: str
    total_centavos: int
    paciente_id: int | None = None
    referencia_tipo: str | None = None
    referencia_id: int | None = None


class CargoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    persona_id: int
    paciente_id: int | None
    concepto: str
    total_inicial: int
    origen: str
    referencia_tipo: str | None
    referencia_id: int | None
    creado_por: int
    created_at: datetime


class CargoDetalleOut(BaseModel):
    id: int
    persona_id: int
    paciente_id: int | None
    concepto: str
    total_inicial: int
    origen: str
    referencia_tipo: str | None
    referencia_id: int | None
    creado_por: int
    created_at: datetime
    total_vigente: int
    total_pagado: int
    saldo: int


class AjustePrecioCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nuevo_total_centavos: int
    motivo: str


class AjustePrecioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cargo_id: int
    precio_anterior: int
    precio_nuevo: int
    motivo: str
    usuario_id: int
    created_at: datetime


class PagoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monto_centavos: int
    medio: str
    es_sena: bool = False
    fecha: date | None = None


class PagoRevertir(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=1)


class PagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cargo_id: int
    monto: int
    tipo: str
    pago_revertido_id: int | None
    medio_pago_id: int
    es_sena: bool
    fecha: date
    usuario_id: int
    empleado_id: int | None
    clave_idempotencia: str | None
    motivo: str | None = None
    created_at: datetime


class CargoCuentaOut(BaseModel):
    cargo: CargoDetalleOut
    pagos: list[PagoOut]


class CuentaClienteOut(BaseModel):
    persona_id: int
    saldo_total: int
    cargos: list[CargoCuentaOut]


class CuentaPacienteOut(BaseModel):
    paciente_id: int
    saldo_total: int
    cargos: list[CargoCuentaOut]


class PersonaDeudorOut(BaseModel):
    id: int
    nombre: str
    apellido: str
    telefono_principal: str | None


class DeudorOut(BaseModel):
    persona: PersonaDeudorOut
    saldo_total_centavos: int
    cantidad_cargos_pendientes: int
    deuda_mas_antigua: date
    saldo_migracion_centavos: int


class ResumenDeuda(BaseModel):
    debe: bool
    saldo_total_centavos: int
    cargos_pendientes: int
    deuda_mas_antigua: date | None
    incluye_migracion: bool


class GastoExternoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empleado_id: int
    descripcion: str = Field(min_length=1)
    monto_centavos: int = Field(gt=0, strict=True)
    fecha: date
    cargo_id: int | None = None
    pago_id: int | None = None


class GastoAnular(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=1)


class GastoOut(BaseModel):
    id: int
    empleado_id: int
    empleado_nombre: str
    descripcion: str
    monto_centavos: int
    fecha: date
    cargo_id: int | None
    pago_id: int | None
    registrado_por: int
    created_at: datetime
    anulado_en: datetime | None
    anulado_por: int | None
    motivo_anulacion: str | None


class ListaGastosOut(BaseModel):
    items: list[GastoOut]
    total_centavos: int
