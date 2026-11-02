"""Acceso a datos de historia clínica."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.clinica.models import (
    Adjunto,
    Atencion,
    EstadoTurno,
    Estudio,
    FranjaTurnoPersonal,
    HorarioAtencion,
    TipoAtencion,
    Turno,
    TurnoPersonal,
    TurnoPersonalDef,
    VacunaAplicada,
)
from app.modules.clinica.schemas import HorarioAtencionIn, TurnoPersonalDefIn


def listar_horarios(db: Session) -> list[HorarioAtencion]:
    consulta = select(HorarioAtencion).order_by(
        HorarioAtencion.dia_semana, HorarioAtencion.hora_desde
    )
    return list(db.execute(consulta).scalars())


def reemplazar_horarios(
    db: Session, horarios: list[HorarioAtencionIn]
) -> list[HorarioAtencion]:
    db.query(HorarioAtencion).delete()
    nuevas = [
        HorarioAtencion(
            dia_semana=item.dia_semana,
            hora_desde=item.hora_desde,
            hora_hasta=item.hora_hasta,
        )
        for item in horarios
    ]
    db.add_all(nuevas)
    db.flush()
    return nuevas


def listar_definiciones_turno_personal(db: Session) -> list[TurnoPersonalDef]:
    consulta = select(TurnoPersonalDef).order_by(TurnoPersonalDef.turno)
    return list(db.execute(consulta).scalars())


def reemplazar_definiciones_turno_personal(
    db: Session, definiciones: list[TurnoPersonalDefIn]
) -> list[TurnoPersonalDef]:
    db.query(TurnoPersonalDef).delete()
    nuevas = [
        TurnoPersonalDef(
            turno=item.turno,
            hora_desde=item.hora_desde,
            hora_hasta=item.hora_hasta,
        )
        for item in definiciones
    ]
    db.add_all(nuevas)
    db.flush()
    return nuevas


def listar_turnos_personal(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    empleado_id: int | None = None,
) -> list[TurnoPersonal]:
    consulta = select(TurnoPersonal)
    if desde is not None:
        consulta = consulta.where(TurnoPersonal.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(TurnoPersonal.fecha <= hasta)
    if empleado_id is not None:
        consulta = consulta.where(TurnoPersonal.empleado_id == empleado_id)
    consulta = consulta.order_by(
        TurnoPersonal.fecha, TurnoPersonal.turno, TurnoPersonal.empleado_id
    )
    return list(db.execute(consulta).scalars())


def obtener_turno_personal(
    db: Session,
    empleado_id: int,
    fecha: date,
    turno: FranjaTurnoPersonal,
) -> TurnoPersonal | None:
    return db.get(TurnoPersonal, (empleado_id, fecha, turno))


def crear_turno_personal(db: Session, turno: TurnoPersonal) -> TurnoPersonal:
    db.add(turno)
    db.flush()
    return turno


def eliminar_turno_personal(db: Session, turno: TurnoPersonal) -> None:
    db.delete(turno)
    db.flush()


def obtener_turno(db: Session, turno_id: int) -> Turno | None:
    return db.get(Turno, turno_id)


def crear_turno(db: Session, turno: Turno) -> Turno:
    db.add(turno)
    db.flush()
    return turno


def listar_turnos(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    veterinario_id: int | None = None,
    paciente_id: int | None = None,
    estado: EstadoTurno | None = None,
) -> list[Turno]:
    consulta = select(Turno)
    if desde is not None:
        consulta = consulta.where(Turno.inicio >= datetime.combine(desde, time.min))
    if hasta is not None:
        limite = datetime.combine(hasta + timedelta(days=1), time.min)
        consulta = consulta.where(Turno.inicio < limite)
    if veterinario_id is not None:
        consulta = consulta.where(Turno.veterinario_empleado_id == veterinario_id)
    if paciente_id is not None:
        consulta = consulta.where(Turno.paciente_id == paciente_id)
    if estado is not None:
        consulta = consulta.where(Turno.estado == estado)
    consulta = consulta.order_by(Turno.inicio, Turno.id)
    return list(db.execute(consulta).scalars())


def turno_solapado(
    db: Session,
    *,
    paciente_id: int,
    veterinario_id: int,
    inicio: datetime,
    fin: datetime,
    excluir_id: int | None = None,
) -> Turno | None:
    consulta = select(Turno).where(
        Turno.estado.in_(
            (
                EstadoTurno.PROGRAMADO,
                EstadoTurno.PENDIENTE_EXTERNO,
                EstadoTurno.CONFIRMADO,
            )
        ),
        or_(
            Turno.paciente_id == paciente_id,
            Turno.veterinario_empleado_id == veterinario_id,
        ),
        Turno.inicio < fin,
        Turno.fin > inicio,
    )
    if excluir_id is not None:
        consulta = consulta.where(Turno.id != excluir_id)
    return db.execute(consulta.order_by(Turno.id).limit(1)).scalar_one_or_none()


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


def crear_estudio(db: Session, estudio: Estudio) -> Estudio:
    db.add(estudio)
    db.flush()
    return estudio


def obtener_estudio(db: Session, estudio_id: int) -> Estudio | None:
    return db.get(Estudio, estudio_id)


def listar_estudios(db: Session, paciente_id: int) -> list[Estudio]:
    consulta = (
        select(Estudio)
        .where(Estudio.paciente_id == paciente_id)
        .order_by(Estudio.fecha.desc(), Estudio.id.desc())
    )
    return list(db.execute(consulta).scalars())


def listar_adjuntos(db: Session, estudio_ids: list[int]) -> list[Adjunto]:
    if not estudio_ids:
        return []
    consulta = (
        select(Adjunto)
        .where(Adjunto.estudio_id.in_(estudio_ids))
        .order_by(Adjunto.created_at, Adjunto.id)
    )
    return list(db.execute(consulta).scalars())


def obtener_adjunto(db: Session, adjunto_id: int) -> Adjunto | None:
    return db.get(Adjunto, adjunto_id)


def crear_adjunto(db: Session, adjunto: Adjunto) -> Adjunto:
    db.add(adjunto)
    db.flush()
    return adjunto
