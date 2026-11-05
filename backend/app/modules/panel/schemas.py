"""Schemas del módulo panel financiero (T-46).

Todos los importes están en centavos. Las deudas se informan aparte de la
rentabilidad (RN-40).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CalidadDatosOut(BaseModel):
    cargos_otro: int
    cargos_migrados: int
    total_cargos: int


class ResumenPanelOut(BaseModel):
    desde: date
    hasta: date
    ingresos_centavos: int
    ingresos_migracion_centavos: int
    egresos_operativos_centavos: int
    # Con filtro por servicio los egresos operativos no se reparten.
    egresos_operativos_sin_asignar_centavos: int
    gastos_externos_centavos: int
    rentabilidad_neta_centavos: int | None
    rentabilidad_neta_motivo: str | None
    calidad_datos: CalidadDatosOut


class PuntoSerieOut(BaseModel):
    clave: str
    ingresos_centavos: int
    egresos_operativos_centavos: int


class SeriePanelOut(BaseModel):
    agrupar: str
    desde: date
    hasta: date
    puntos: list[PuntoSerieOut]


class IngresoPorServicioOut(BaseModel):
    tipo_servicio: str
    ingresos_centavos: int


class IngresoPorMedioOut(BaseModel):
    medio: str
    ingresos_centavos: int


class IngresoHistorialOut(BaseModel):
    id: int
    cargo_id: int
    monto_centavos: int
    tipo: str
    estado: str
    fecha: date
    medio: str
    medio_pago_id: int
    es_sena: bool
    concepto: str
    tipo_servicio: str
    origen: str
    usuario_id: int
    empleado_id: int | None
    motivo: str | None
    created_at: datetime


class MayorDeudorOut(BaseModel):
    persona_id: int
    nombre: str
    apellido: str
    saldo_total_centavos: int
    migracion_centavos: int
    cantidad_cargos_pendientes: int
    deuda_mas_antigua: date


class DeudasPanelOut(BaseModel):
    total_adeudado_centavos: int
    cantidad_clientes: int
    deuda_migracion_centavos: int
    mayores_deudores: list[MayorDeudorOut]


class ServicioClienteOut(BaseModel):
    cargo_id: int
    tipo_servicio: str
    concepto: str
    total_centavos: int
    pagado_centavos: int
    saldo_centavos: int
    ajustes: int


class DetalleClienteOut(BaseModel):
    persona_id: int
    nombre: str
    apellido: str
    servicios: list[ServicioClienteOut]


class CategoriaEgresoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    activa: bool


class CategoriaEgresoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=80)


class CategoriaEgresoActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activa: bool


class EgresoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date
    monto_centavos: int = Field(gt=0, strict=True)
    categoria_id: int
    descripcion: str = Field(min_length=1, max_length=255)
    medio_pago_id: int | None = None


class EgresoAnular(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=1, max_length=255)


class EgresoOut(BaseModel):
    id: int
    fecha: date
    monto_centavos: int
    categoria_id: int
    categoria_nombre: str
    descripcion: str
    medio_pago_id: int | None
    registrado_por: int
    created_at: datetime
    anulado_en: datetime | None
    anulado_por: int | None
    motivo_anulacion: str | None
