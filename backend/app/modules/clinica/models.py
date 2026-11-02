"""Modelos de historia clínica, separados de los cargos y pagos."""

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class TipoAtencion(str, Enum):
    CONSULTA = "CONSULTA"
    VACUNA = "VACUNA"
    CIRUGIA = "CIRUGIA"
    TRATAMIENTO = "TRATAMIENTO"
    ESTUDIO = "ESTUDIO"


class TipoTurnoMedico(str, Enum):
    CONSULTA = "CONSULTA"
    VACUNA = "VACUNA"
    CIRUGIA = "CIRUGIA"
    ESTUDIO = "ESTUDIO"
    CONTROL = "CONTROL"


class EstadoTurno(str, Enum):
    PROGRAMADO = "PROGRAMADO"
    PENDIENTE_EXTERNO = "PENDIENTE_EXTERNO"
    CONFIRMADO = "CONFIRMADO"
    ATENDIDO = "ATENDIDO"
    CANCELADO = "CANCELADO"
    AUSENTE = "AUSENTE"


class FranjaTurnoPersonal(str, Enum):
    MANANA = "MANANA"
    TARDE = "TARDE"
    NOCHE = "NOCHE"


class OrigenAtencion(str, Enum):
    NORMAL = "NORMAL"
    MIGRACION = "MIGRACION"


class TipoEstudio(str, Enum):
    RADIOGRAFIA = "RADIOGRAFIA"
    ECOGRAFIA = "ECOGRAFIA"
    ANALISIS = "ANALISIS"
    OTRO = "OTRO"


class Atencion(Base):
    __tablename__ = "atencion"
    __table_args__ = (
        CheckConstraint(
            "tipo != 'CIRUGIA' OR cirujano_externo_id IS NOT NULL",
            name="ck_atencion_cirugia_cirujano",
        ),
        CheckConstraint(
            "tipo = 'CIRUGIA' OR cirujano_externo_id IS NULL",
            name="ck_atencion_sin_cirujano_no_cirugia",
        ),
        Index("ix_atencion_paciente_fecha", "paciente_id", "fecha_hora", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), nullable=False)
    tipo: Mapped[TipoAtencion] = mapped_column(
        SAEnum(
            TipoAtencion,
            name="tipo_atencion",
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    veterinario_empleado_id: Mapped[int] = mapped_column(
        ForeignKey("empleado.persona_id"), nullable=False
    )
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostico: Mapped[str | None] = mapped_column(Text, nullable=True)
    tratamiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    cirujano_externo_id: Mapped[int | None] = mapped_column(
        ForeignKey("empleado.persona_id"), nullable=True
    )
    cargo_id: Mapped[int | None] = mapped_column(ForeignKey("cargo.id"), nullable=True)
    origen: Mapped[OrigenAtencion] = mapped_column(
        SAEnum(
            OrigenAtencion,
            name="origen_atencion",
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=OrigenAtencion.NORMAL,
        server_default=OrigenAtencion.NORMAL.value,
    )
    texto_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    rectifica_a_id: Mapped[int | None] = mapped_column(ForeignKey("atencion.id"), nullable=True)
    rectificada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VacunaAplicada(Base):
    __tablename__ = "vacuna_aplicada"
    __table_args__ = (UniqueConstraint("atencion_id", name="uq_vacuna_aplicada_atencion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    atencion_id: Mapped[int] = mapped_column(ForeignKey("atencion.id"), nullable=False)
    nombre_vacuna: Mapped[str] = mapped_column(String(100), nullable=False)
    lote: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_aplicacion: Mapped[date] = mapped_column(Date, nullable=False)
    proxima_dosis: Mapped[date | None] = mapped_column(Date, nullable=True)


class Estudio(Base):
    __tablename__ = "estudio"
    __table_args__ = (Index("ix_estudio_paciente_fecha", "paciente_id", "fecha", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), nullable=False)
    atencion_id: Mapped[int | None] = mapped_column(ForeignKey("atencion.id"), nullable=True)
    tipo: Mapped[TipoEstudio] = mapped_column(
        SAEnum(
            TipoEstudio,
            name="tipo_estudio",
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    realizado_por_empleado_id: Mapped[int] = mapped_column(
        ForeignKey("empleado.persona_id"), nullable=False
    )
    cargo_id: Mapped[int | None] = mapped_column(ForeignKey("cargo.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Adjunto(Base):
    __tablename__ = "adjunto"
    __table_args__ = (Index("ix_adjunto_estudio_id", "estudio_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    estudio_id: Mapped[int] = mapped_column(ForeignKey("estudio.id"), nullable=False)
    nombre_original: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HorarioAtencion(Base):
    __tablename__ = "horario_atencion"
    __table_args__ = (
        CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_horario_dia_semana"),
        CheckConstraint("hora_desde < hora_hasta", name="ck_horario_rango"),
        Index("ix_horario_atencion_dia", "dia_semana", "hora_desde"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dia_semana: Mapped[int] = mapped_column(nullable=False)
    hora_desde: Mapped[time] = mapped_column(Time(), nullable=False)
    hora_hasta: Mapped[time] = mapped_column(Time(), nullable=False)


class TurnoPersonalDef(Base):
    __tablename__ = "turno_personal_def"
    __table_args__ = (
        UniqueConstraint("turno", name="uq_turno_personal_def_turno"),
        CheckConstraint("hora_desde != hora_hasta", name="ck_turno_personal_def_rango"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    turno: Mapped[FranjaTurnoPersonal] = mapped_column(
        SAEnum(
            FranjaTurnoPersonal,
            name="franja_turno_personal",
            native_enum=False,
            length=10,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    hora_desde: Mapped[time] = mapped_column(Time(), nullable=False)
    hora_hasta: Mapped[time] = mapped_column(Time(), nullable=False)


class TurnoPersonal(Base):
    __tablename__ = "turno_personal"
    __table_args__ = (
        Index("ix_turno_personal_fecha_turno", "fecha", "turno"),
    )

    empleado_id: Mapped[int] = mapped_column(
        ForeignKey("empleado.persona_id"), primary_key=True
    )
    fecha: Mapped[date] = mapped_column(Date(), primary_key=True)
    turno: Mapped[FranjaTurnoPersonal] = mapped_column(
        SAEnum(
            FranjaTurnoPersonal,
            name="franja_turno_personal",
            native_enum=False,
            length=10,
            create_constraint=True,
            validate_strings=True,
        ),
        primary_key=True,
    )


class Turno(Base):
    __tablename__ = "turno"
    __table_args__ = (
        CheckConstraint("inicio < fin", name="ck_turno_rango"),
        Index("ix_turno_veterinario_inicio", "veterinario_empleado_id", "inicio"),
        Index("ix_turno_paciente_inicio", "paciente_id", "inicio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), nullable=False)
    tipo: Mapped[TipoTurnoMedico] = mapped_column(
        SAEnum(
            TipoTurnoMedico,
            name="tipo_turno_medico",
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    veterinario_empleado_id: Mapped[int] = mapped_column(
        ForeignKey("empleado.persona_id"), nullable=False
    )
    inicio: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    fin: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    estado: Mapped[EstadoTurno] = mapped_column(
        SAEnum(
            EstadoTurno,
            name="estado_turno",
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=EstadoTurno.PROGRAMADO,
        server_default=EstadoTurno.PROGRAMADO.value,
    )
    motivo: Mapped[str | None] = mapped_column(Text(), nullable=True)
    atencion_id: Mapped[int | None] = mapped_column(ForeignKey("atencion.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
