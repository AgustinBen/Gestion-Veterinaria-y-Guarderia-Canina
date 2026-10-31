from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import HabilitacionEmergencia, Ocupacion


def contar_ocupacion(db: Session, fecha: date, franja: Franja) -> int:
    stmt = select(func.count(Ocupacion.id)).where(
        Ocupacion.fecha == fecha,
        Ocupacion.franja == franja,
    )
    return db.execute(stmt).scalar_one()


def listar_ocupaciones(
    db: Session,
    desde: date,
    hasta: date,
    *,
    paciente_ids: list[int] | None = None,
) -> list[Ocupacion]:
    if paciente_ids == []:
        return []

    stmt = select(Ocupacion).where(
        Ocupacion.fecha >= desde,
        Ocupacion.fecha <= hasta,
    )
    if paciente_ids is not None:
        stmt = stmt.where(Ocupacion.paciente_id.in_(paciente_ids))
    stmt = stmt.order_by(Ocupacion.fecha, Ocupacion.franja, Ocupacion.paciente_id)
    return list(db.execute(stmt).scalars().all())


def contar_habilitaciones(
    db: Session,
    fecha: date,
    franja: Franja,
) -> int:
    stmt = select(func.count(HabilitacionEmergencia.id)).where(
        HabilitacionEmergencia.fecha == fecha,
        HabilitacionEmergencia.franja == franja,
    )
    return db.execute(stmt).scalar_one()


def contar_habilitaciones_por_franja(
    db: Session,
    desde: date,
    hasta: date,
) -> dict[tuple[date, Franja], int]:
    stmt = (
        select(
            HabilitacionEmergencia.fecha,
            HabilitacionEmergencia.franja,
            func.count(HabilitacionEmergencia.id),
        )
        .where(
            HabilitacionEmergencia.fecha >= desde,
            HabilitacionEmergencia.fecha <= hasta,
        )
        .group_by(HabilitacionEmergencia.fecha, HabilitacionEmergencia.franja)
    )
    return {
        (fecha, franja): cantidad
        for fecha, franja, cantidad in db.execute(stmt).all()
    }
