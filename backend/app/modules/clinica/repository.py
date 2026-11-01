"""Acceso a datos de historia clínica."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.clinica.models import Atencion, TipoAtencion, VacunaAplicada


def crear_atencion(db: Session, atencion: Atencion) -> Atencion:
    db.add(atencion)
    db.flush()
    return atencion


def obtener_atencion(db: Session, atencion_id: int) -> Atencion | None:
    return db.get(Atencion, atencion_id)


def obtener_vacuna(db: Session, atencion_id: int) -> VacunaAplicada | None:
    return db.execute(
        select(VacunaAplicada).where(VacunaAplicada.atencion_id == atencion_id)
    ).scalar_one_or_none()


def listar_atenciones(
    db: Session,
    paciente_id: int,
    *,
    tipo: TipoAtencion | None,
    desde: date | None,
    hasta: date | None,
    limit: int,
    offset: int,
) -> list[Atencion]:
    consulta = select(Atencion).where(Atencion.paciente_id == paciente_id)
    if tipo is not None:
        consulta = consulta.where(Atencion.tipo == tipo)
    if desde is not None:
        consulta = consulta.where(func.date(Atencion.fecha_hora) >= desde.isoformat())
    if hasta is not None:
        consulta = consulta.where(func.date(Atencion.fecha_hora) <= hasta.isoformat())
    consulta = consulta.order_by(Atencion.fecha_hora.desc(), Atencion.id.desc())
    consulta = consulta.limit(limit).offset(offset)
    return list(db.execute(consulta).scalars())


def ultima_atencion(db: Session, paciente_id: int) -> Atencion | None:
    consulta = (
        select(Atencion)
        .where(
            Atencion.paciente_id == paciente_id,
            Atencion.rectificada.is_(False),
        )
        .order_by(Atencion.fecha_hora.desc(), Atencion.id.desc())
        .limit(1)
    )
    return db.execute(consulta).scalar_one_or_none()


def listar_vacunas(db: Session, paciente_id: int) -> list[VacunaAplicada]:
    consulta = (
        select(VacunaAplicada)
        .join(Atencion, Atencion.id == VacunaAplicada.atencion_id)
        .where(Atencion.paciente_id == paciente_id)
        .order_by(
            VacunaAplicada.fecha_aplicacion.desc(),
            VacunaAplicada.id.desc(),
        )
    )
    return list(db.execute(consulta).scalars())
