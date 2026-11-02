"""Schemas del módulo panel financiero (T-46).

Todos los importes están en centavos. Las deudas se informan aparte de la
rentabilidad (RN-40).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


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
