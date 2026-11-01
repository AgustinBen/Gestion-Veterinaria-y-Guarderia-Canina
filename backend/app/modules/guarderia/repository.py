from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import (
    CancelacionReserva,
    EstadoReserva,
    HabilitacionEmergencia,
    Ocupacion,
    Reserva,
    ReservaPaciente,
)


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


def obtener_habilitacion_por_clave(
    db: Session,
    clave_idempotencia: str,
) -> HabilitacionEmergencia | None:
    stmt = select(HabilitacionEmergencia).where(
        HabilitacionEmergencia.clave_idempotencia == clave_idempotencia
    )
    return db.execute(stmt).scalar_one_or_none()


def crear_habilitacion(db: Session, habilitacion: HabilitacionEmergencia) -> None:
    db.add(habilitacion)
    db.flush()


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


def obtener_reserva(db: Session, reserva_id: int) -> Reserva | None:
    return db.get(Reserva, reserva_id)


def obtener_reserva_por_clave(db: Session, clave: str) -> Reserva | None:
    stmt = select(Reserva).where(Reserva.clave_idempotencia == clave)
    return db.execute(stmt).scalar_one_or_none()


def obtener_reserva_por_cargo(db: Session, cargo_id: int) -> Reserva | None:
    stmt = select(Reserva).where(Reserva.cargo_id == cargo_id)
    return db.execute(stmt).scalar_one_or_none()


def obtener_cancelacion_por_clave(
    db: Session,
    clave_idempotencia: str,
) -> CancelacionReserva | None:
    stmt = select(CancelacionReserva).where(
        CancelacionReserva.clave_idempotencia == clave_idempotencia
    )
    return db.execute(stmt).scalar_one_or_none()


def crear_cancelacion(
    db: Session,
    cancelacion: CancelacionReserva,
) -> None:
    db.add(cancelacion)
    db.flush()


def eliminar_ocupaciones_reserva(db: Session, reserva_id: int) -> None:
    stmt = select(Ocupacion).where(Ocupacion.reserva_id == reserva_id)
    for ocupacion in db.execute(stmt).scalars():
        db.delete(ocupacion)
    db.flush()


def listar_reservas(
    db: Session,
    *,
    desde: date | None,
    hasta: date | None,
    estado: EstadoReserva | None,
    persona_id: int | None,
) -> list[Reserva]:
    stmt = select(Reserva)
    if desde is not None:
        stmt = stmt.where(Reserva.hasta_fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(Reserva.desde_fecha <= hasta)
    if estado is not None:
        stmt = stmt.where(Reserva.estado == estado)
    if persona_id is not None:
        stmt = stmt.where(Reserva.tutor_persona_id == persona_id)
    stmt = stmt.order_by(Reserva.desde_fecha, Reserva.desde_franja, Reserva.id)
    return list(db.execute(stmt).scalars().all())


def pacientes_de_reserva(
    db: Session, reserva_id: int
) -> list[ReservaPaciente]:
    stmt = (
        select(ReservaPaciente)
        .where(ReservaPaciente.reserva_id == reserva_id)
        .order_by(ReservaPaciente.paciente_id)
    )
    return list(db.execute(stmt).scalars().all())


def crear_reserva(db: Session, reserva: Reserva) -> None:
    db.add(reserva)
    db.flush()


def agregar_pacientes_reserva(
    db: Session, pacientes: list[ReservaPaciente]
) -> None:
    db.add_all(pacientes)
    db.flush()


def agregar_ocupaciones(db: Session, ocupaciones: list[Ocupacion]) -> None:
    db.add_all(ocupaciones)
    db.flush()
