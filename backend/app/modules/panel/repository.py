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


def listar_categorias(
    db: Session, *, activa: bool | None = None
) -> list[models.CategoriaEgreso]:
    stmt = select(models.CategoriaEgreso).order_by(models.CategoriaEgreso.nombre)
    if activa is not None:
        stmt = stmt.where(models.CategoriaEgreso.activa.is_(activa))
    return list(db.execute(stmt).scalars().all())


def obtener_categoria(
    db: Session, categoria_id: int
) -> models.CategoriaEgreso | None:
    return db.get(models.CategoriaEgreso, categoria_id)


def categoria_por_normalizado(
    db: Session, nombre_normalizado: str
) -> models.CategoriaEgreso | None:
    stmt = select(models.CategoriaEgreso).where(
        models.CategoriaEgreso.nombre_normalizado == nombre_normalizado
    )
    return db.execute(stmt).scalar_one_or_none()


def crear_categoria(
    db: Session, *, nombre: str, nombre_normalizado: str
) -> models.CategoriaEgreso:
    categoria = models.CategoriaEgreso(
        nombre=nombre, nombre_normalizado=nombre_normalizado, activa=True
    )
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def guardar_categoria(
    db: Session, categoria: models.CategoriaEgreso
) -> models.CategoriaEgreso:
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def crear_egreso(
    db: Session,
    *,
    fecha: date,
    monto_centavos: int,
    categoria_id: int,
    descripcion: str,
    medio_pago_id: int | None,
    registrado_por: int,
) -> models.Egreso:
    egreso = models.Egreso(
        fecha=fecha,
        monto_centavos=monto_centavos,
        categoria_id=categoria_id,
        descripcion=descripcion,
        medio_pago_id=medio_pago_id,
        registrado_por=registrado_por,
    )
    db.add(egreso)
    db.commit()
    db.refresh(egreso)
    return egreso


def obtener_egreso(db: Session, egreso_id: int) -> models.Egreso | None:
    return db.get(models.Egreso, egreso_id)


def guardar_egreso(db: Session, egreso: models.Egreso) -> models.Egreso:
    db.add(egreso)
    db.commit()
    db.refresh(egreso)
    return egreso


def listar_egresos(
    db: Session,
    *,
    desde: date,
    hasta: date,
    categoria_id: int | None = None,
    limite: int = 200,
) -> list[Any]:
    filtros = [models.Egreso.fecha >= desde, models.Egreso.fecha <= hasta]
    if categoria_id is not None:
        filtros.append(models.Egreso.categoria_id == categoria_id)
    stmt = (
        select(models.Egreso, models.CategoriaEgreso.nombre.label("categoria_nombre"))
        .join(
            models.CategoriaEgreso,
            models.CategoriaEgreso.id == models.Egreso.categoria_id,
        )
        .where(*filtros)
        .order_by(models.Egreso.fecha.desc(), models.Egreso.id.desc())
        .limit(limite)
    )
    return list(db.execute(stmt).all())


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
