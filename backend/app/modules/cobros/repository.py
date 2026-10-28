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
