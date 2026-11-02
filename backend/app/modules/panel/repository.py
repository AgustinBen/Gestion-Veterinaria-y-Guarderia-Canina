"""Repositorio del módulo panel.

Solo lee las tablas propias (egresos). Los ingresos, gastos a externos y
deudas se piden al service público del módulo cobros.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.panel import models


def _filtros_egresos(
    *, desde: date, hasta: date, medio_pago_id: int | None
) -> list[Any]:
    filtros: list[Any] = [
        models.Egreso.anulado_en.is_(None),
        models.Egreso.fecha >= desde,
        models.Egreso.fecha <= hasta,
    ]
    if medio_pago_id is not None:
        filtros.append(models.Egreso.medio_pago_id == medio_pago_id)
    return filtros


def total_egresos(
    db: Session, *, desde: date, hasta: date, medio_pago_id: int | None = None
) -> int:
    stmt = select(func.coalesce(func.sum(models.Egreso.monto_centavos), 0)).where(
        *_filtros_egresos(desde=desde, hasta=hasta, medio_pago_id=medio_pago_id)
    )
    return int(db.execute(stmt).scalar_one())


def egresos_agregados(
    db: Session,
    *,
    desde: date,
    hasta: date,
    agrupar: str,
    medio_pago_id: int | None,
) -> list[Any]:
    clave: Any
    grupo: Any
    if agrupar == "dia":
        clave = models.Egreso.fecha.label("clave")
        grupo = models.Egreso.fecha
    elif agrupar == "mes":
        clave = func.strftime("%Y-%m", models.Egreso.fecha).label("clave")
        grupo = func.strftime("%Y-%m", models.Egreso.fecha)
    else:  # pragma: no cover - el service valida antes
        raise ValueError(f"Agrupación inválida: {agrupar}")

    stmt = (
        select(
            clave,
            func.coalesce(func.sum(models.Egreso.monto_centavos), 0).label(
                "monto_centavos"
            ),
        )
        .where(
            *_filtros_egresos(
                desde=desde, hasta=hasta, medio_pago_id=medio_pago_id
            )
        )
        .group_by(grupo)
        .order_by(grupo)
    )
    return list(db.execute(stmt).all())
