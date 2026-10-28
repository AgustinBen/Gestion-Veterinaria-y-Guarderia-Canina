"""Sembrado de catálogos del módulo cobros."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cobros import models

MEDIOS_PAGO = [
    ("EFECTIVO", "Efectivo"),
    ("DEBITO", "Débito"),
    ("TRANSFERENCIA", "Transferencia"),
    ("MERCADO_PAGO", "Mercado Pago"),
]


def sembrar_medios_pago(db: Session) -> None:
    for codigo, nombre in MEDIOS_PAGO:
        existente = db.execute(
            select(models.MedioPago).where(models.MedioPago.codigo == codigo)
        ).scalar_one_or_none()
        if existente is None:
            db.add(models.MedioPago(codigo=codigo, nombre=nombre))
    db.commit()
