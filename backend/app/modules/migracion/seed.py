"""Parámetros configurables del módulo de migración (T-16).

Ningún valor de negocio se hardcodea: la fecha de corte y el peso máximo viven
en configuración y los tests siembran los suyos.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import parametros

CLAVE_FECHA_CORTE = "migracion.fecha_corte"
CLAVE_PESO_MAX_KG = "migracion.peso_max_kg"


def sembrar_parametros_migracion(db: Session) -> None:
    """Registra las claves si faltan; no pisa valores ya definidos."""
    parametros.registrar_parametro(
        db,
        CLAVE_FECHA_CORTE,
        "",
        "str",
        modulo="migracion",
        descripcion="Fecha de corte ISO (aaaa-mm-dd) para calcular la edad de las mascotas",
    )
    parametros.registrar_parametro(
        db,
        CLAVE_PESO_MAX_KG,
        Decimal("100"),
        "decimal",
        modulo="migracion",
        descripcion="Peso máximo aceptado al migrar (kg); fuera de rango va a revisión",
    )
