"""Seeds del módulo padrón."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import parametros
from app.modules.padron import models, normalizacion


def sembrar_parametros_padron(db: Session) -> None:
    """Siembra los parámetros configurables del módulo (sin hardcodear reglas)."""
    parametros.registrar_parametro(
        db,
        normalizacion.CLAVE_CODIGO_AREA_DEFECTO,
        "11",
        "str",
        modulo="padron",
        descripcion="Código de área que completa los teléfonos de 8 dígitos",
    )
    parametros.registrar_parametro(
        db,
        normalizacion.CLAVE_UMBRAL_NOMBRE_PARECIDO,
        Decimal("0.85"),
        "decimal",
        modulo="padron",
        descripcion="Similitud mínima para avisar por nombre parecido (RN-06)",
    )


def sembrar_especies_tamanios_tipo_contacto(db: Session) -> None:
    sembrar_parametros_padron(db)
    if db.query(models.Especie).count() == 0:
        db.add_all(
            [
                models.Especie(nombre="Perro"),
                models.Especie(nombre="Gato"),
            ]
        )
    if db.query(models.Tamanio).count() == 0:
        db.add_all(
            [
                models.Tamanio(nombre="Chico"),
                models.Tamanio(nombre="Mediano"),
                models.Tamanio(nombre="Grande"),
            ]
        )
    if db.query(models.TipoContacto).count() == 0:
        db.add_all(
            [
                models.TipoContacto(nombre="TITULAR"),
                models.TipoContacto(nombre="CONTACTO ALTERNATIVO"),
            ]
        )
    db.flush()
