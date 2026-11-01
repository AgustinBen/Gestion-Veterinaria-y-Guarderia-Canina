"""Acceso a la tabla propia ``migracion_registro`` (T-16).

No hace commit: la transacción la controla ``carga``. Nunca toca tablas de
otros módulos.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.migracion.models import MigracionRegistro


def obtener(db: Session, hoja: str, fila: int) -> MigracionRegistro | None:
    stmt = select(MigracionRegistro).where(
        MigracionRegistro.hoja == hoja, MigracionRegistro.fila == fila
    )
    return db.execute(stmt).scalar_one_or_none()


def crear(db: Session, registro: MigracionRegistro) -> MigracionRegistro:
    db.add(registro)
    db.flush()
    return registro


def actualizar(
    db: Session, registro: MigracionRegistro, datos: Mapping[str, Any]
) -> MigracionRegistro:
    for campo, valor in datos.items():
        setattr(registro, campo, valor)
    db.flush()
    return registro


def obtener_por_entidad(
    db: Session, entidad: str, entidad_id: int
) -> MigracionRegistro | None:
    stmt = (
        select(MigracionRegistro)
        .where(
            MigracionRegistro.entidad == entidad,
            MigracionRegistro.entidad_id == entidad_id,
        )
        .order_by(MigracionRegistro.fila)
    )
    return db.execute(stmt).scalars().first()


def listar_por_hoja(db: Session, hoja: str) -> list[MigracionRegistro]:
    stmt = (
        select(MigracionRegistro)
        .where(MigracionRegistro.hoja == hoja)
        .order_by(MigracionRegistro.fila)
    )
    return list(db.execute(stmt).scalars())
