"""Repositorio del módulo cobros. Sin funciones para modificar/borrar cargo, ajuste_precio o pago."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select
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
    pagos = db.execute(
        select(func.coalesce(func.sum(models.Pago.monto), 0)).where(
            models.Pago.cargo_id == cargo_id, models.Pago.tipo == models.TipoPago.PAGO
        )
    ).scalar_one()
    reversos = db.execute(
        select(func.coalesce(func.sum(models.Pago.monto), 0)).where(
            models.Pago.cargo_id == cargo_id, models.Pago.tipo == models.TipoPago.REVERSO
        )
    ).scalar_one()
    return int(pagos) - int(reversos)


def saldo(db: Session, cargo_id: int) -> int:
    return total_vigente(db, cargo_id) - total_pagado(db, cargo_id)


def _cargos_con_saldo() -> Any:
    ultimo_ajuste = (
        select(models.AjustePrecio.precio_nuevo)
        .where(models.AjustePrecio.cargo_id == models.Cargo.id)
        .order_by(models.AjustePrecio.created_at.desc(), models.AjustePrecio.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    total_vigente_expr = func.coalesce(ultimo_ajuste, models.Cargo.total_inicial)
    pagos_netos_expr = func.coalesce(
        func.sum(
            case(
                (models.Pago.tipo == models.TipoPago.PAGO, models.Pago.monto),
                else_=0,
            )
        ),
        0,
    ) - func.coalesce(
        func.sum(
            case(
                (models.Pago.tipo == models.TipoPago.REVERSO, models.Pago.monto),
                else_=0,
            )
        ),
        0,
    )
    return (
        select(
            models.Cargo.id.label("cargo_id"),
            models.Cargo.persona_id.label("persona_id"),
            models.Cargo.origen.label("origen"),
            models.Cargo.created_at.label("created_at"),
            (total_vigente_expr - pagos_netos_expr).label("saldo"),
        )
        .outerjoin(models.Pago, models.Pago.cargo_id == models.Cargo.id)
        .group_by(
            models.Cargo.id,
            models.Cargo.persona_id,
            models.Cargo.origen,
            models.Cargo.created_at,
            models.Cargo.total_inicial,
        )
        .subquery()
    )


def listar_deudores(
    db: Session,
    *,
    orden: str,
    solo_migracion: bool,
    limite: int,
    desplazamiento: int,
) -> list[Any]:
    cargos = _cargos_con_saldo()
    pendientes = select(cargos).where(cargos.c.saldo > 0).subquery()
    migrado = case(
        (pendientes.c.origen == models.OrigenCargo.MIGRACION, pendientes.c.saldo),
        else_=0,
    )
    stmt = select(
        pendientes.c.persona_id,
        func.sum(pendientes.c.saldo).label("saldo_total_centavos"),
        func.count(pendientes.c.cargo_id).label("cantidad_cargos_pendientes"),
        func.min(pendientes.c.created_at).label("deuda_mas_antigua"),
        func.sum(migrado).label("saldo_migracion_centavos"),
    ).group_by(pendientes.c.persona_id)
    if solo_migracion:
        stmt = stmt.having(func.sum(migrado) > 0)
    if orden == "antiguedad":
        stmt = stmt.order_by(
            func.min(pendientes.c.created_at).asc(), pendientes.c.persona_id
        )
    else:
        stmt = stmt.order_by(
            func.sum(pendientes.c.saldo).desc(), pendientes.c.persona_id
        )
    stmt = stmt.limit(limite).offset(desplazamiento)
    return list(db.execute(stmt).all())


def resumen_deuda(db: Session, persona_id: int) -> Any:
    cargos = _cargos_con_saldo()
    pendientes = select(cargos).where(
        cargos.c.persona_id == persona_id, cargos.c.saldo > 0
    ).subquery()
    stmt = select(
        func.coalesce(func.sum(pendientes.c.saldo), 0).label("saldo_total_centavos"),
        func.count(pendientes.c.cargo_id).label("cargos_pendientes"),
        func.min(pendientes.c.created_at).label("deuda_mas_antigua"),
        func.coalesce(
            func.sum(
                case(
                    (
                        pendientes.c.origen == models.OrigenCargo.MIGRACION,
                        pendientes.c.saldo,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("saldo_migracion_centavos"),
    )
    return db.execute(stmt).one()


def crear_ajuste(
    db: Session,
    *,
    cargo_id: int,
    precio_anterior: int,
    precio_nuevo: int,
    motivo: str,
    usuario_id: int,
) -> models.AjustePrecio:
    ajuste = models.AjustePrecio(
        cargo_id=cargo_id,
        precio_anterior=precio_anterior,
        precio_nuevo=precio_nuevo,
        motivo=motivo,
        usuario_id=usuario_id,
    )
    db.add(ajuste)
    db.flush()
    return ajuste


def ajustes_de_cargo(db: Session, cargo_id: int) -> list[models.AjustePrecio]:
    return list(
        db.execute(
            select(models.AjustePrecio)
            .where(models.AjustePrecio.cargo_id == cargo_id)
            .order_by(models.AjustePrecio.created_at.asc(), models.AjustePrecio.id.asc())
        ).scalars().all()
    )


def obtener_cargo(db: Session, cargo_id: int) -> models.Cargo | None:
    return db.get(models.Cargo, cargo_id)


def obtener_pago(db: Session, pago_id: int) -> models.Pago | None:
    return db.get(models.Pago, pago_id)


def obtener_medio_pago_por_codigo(db: Session, codigo: str) -> models.MedioPago | None:
    return db.execute(
        select(models.MedioPago).where(models.MedioPago.codigo == codigo.upper())
    ).scalar_one_or_none()


def obtener_medio_pago(db: Session, medio_pago_id: int) -> models.MedioPago | None:
    return db.get(models.MedioPago, medio_pago_id)


def listar_medios_pago_activos(db: Session) -> list[models.MedioPago]:
    return list(
        db.execute(
            select(models.MedioPago)
            .where(models.MedioPago.activo.is_(True))
            .order_by(models.MedioPago.id)
        ).scalars().all()
    )


def obtener_pago_por_clave_idempotencia(db: Session, clave: str) -> models.Pago | None:
    return db.execute(
        select(models.Pago).where(models.Pago.clave_idempotencia == clave)
    ).scalar_one_or_none()


def tiene_reverso(db: Session, pago_id: int) -> bool:
    existe = db.execute(
        select(models.Pago.id).where(
            models.Pago.tipo == models.TipoPago.REVERSO,
            models.Pago.pago_revertido_id == pago_id,
        )
    ).scalar_one_or_none()
    return existe is not None


def pagos_de_cargo(db: Session, cargo_id: int) -> list[models.Pago]:
    return list(
        db.execute(select(models.Pago).where(models.Pago.cargo_id == cargo_id).order_by(models.Pago.id)).scalars().all()
    )


def cargos_de_persona(db: Session, persona_id: int) -> list[models.Cargo]:
    return list(
        db.execute(select(models.Cargo).where(models.Cargo.persona_id == persona_id).order_by(models.Cargo.id)).scalars().all()
    )


def cargos_de_paciente(db: Session, paciente_id: int) -> list[models.Cargo]:
    return list(
        db.execute(select(models.Cargo).where(models.Cargo.paciente_id == paciente_id).order_by(models.Cargo.id)).scalars().all()
    )
