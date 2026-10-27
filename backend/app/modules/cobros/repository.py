"""Repositorio del módulo cobros. Sin funciones para modificar/borrar cargo, ajuste_precio o pago."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.cobros import models


def total_vigente(db: Session, cargo_id: int) -> int:
    ultimo = db.execute(
        select(models.AjustePrecio.precio_nuevo)
        .where(models.AjustePrecio.cargo_id == cargo_id)
        .order_by(models.AjustePrecio.created_at.desc(), models.AjustePrecio.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if ultimo is not None:
        return int(ultimo)

    cargo = db.get(models.Cargo, cargo_id)
    if cargo is None:
        raise ValueError("Cargo no encontrado")
    return int(cargo.total_inicial)


def total_pagado(db: Session, cargo_id: int) -> int:
    pagos = db.execute(select(func.coalesce(func.sum(models.Pago.monto), 0)).where(models.Pago.cargo_id == cargo_id, models.Pago.tipo == models.TipoPago.PAGO)).scalar_one()
    reversos = db.execute(select(func.coalesce(func.sum(models.Pago.monto), 0)).where(models.Pago.cargo_id == cargo_id, models.Pago.tipo == models.TipoPago.REVERSO)).scalar_one()
    return int(pagos) - int(reversos)


def saldo(db: Session, cargo_id: int) -> int:
    return total_vigente(db, cargo_id) - total_pagado(db, cargo_id)
