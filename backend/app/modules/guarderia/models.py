"""Modelos para reservas y ocupación de guardería."""

from __future__ import annotations

from datetime import date, datetime
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
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.modules.guarderia.franjas import Franja


class EstadoReserva(str, Enum):
    PENDIENTE_SENA = "PENDIENTE_SENA"
    CONFIRMADA = "CONFIRMADA"
    EN_CURSO = "EN_CURSO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"
    AUSENTE = "AUSENTE"


_FRANJA_ENUM = SAEnum(
    Franja,
    name="franja_guarderia",
    native_enum=False,
    length=5,
    create_constraint=True,
    validate_strings=True,
)
_ESTADO_RESERVA_ENUM = SAEnum(
    EstadoReserva,
    name="estado_reserva",
    native_enum=False,
    length=20,
    create_constraint=True,
    validate_strings=True,
)


class Reserva(Base):
    __tablename__ = "reserva"
    __table_args__ = (
        CheckConstraint(
            "desde_fecha < hasta_fecha OR "
            "(desde_fecha = hasta_fecha AND desde_franja <= hasta_franja)",
            name="tramo_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_persona_id: Mapped[int] = mapped_column(
        ForeignKey("persona.id"), nullable=False
    )
    desde_fecha: Mapped[date] = mapped_column(Date, nullable=False)
    desde_franja: Mapped[Franja] = mapped_column(_FRANJA_ENUM, nullable=False)
    hasta_fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hasta_franja: Mapped[Franja] = mapped_column(_FRANJA_ENUM, nullable=False)
    estado: Mapped[EstadoReserva] = mapped_column(_ESTADO_RESERVA_ENUM, nullable=False)
    cargo_id: Mapped[int | None] = mapped_column(ForeignKey("cargo.id"), nullable=True)
    clave_idempotencia: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ReservaPaciente(Base):
    __tablename__ = "reserva_paciente"

    reserva_id: Mapped[int] = mapped_column(
        ForeignKey("reserva.id"), primary_key=True
    )
    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("paciente.id"), primary_key=True
    )
    cuidados_extras: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tipo_cuidado: Mapped[str | None] = mapped_column(Text, nullable=True)


# RN-11b: la regla de plazas por animal vive solo en la función de T-24.
class Ocupacion(Base):
    __tablename__ = "ocupacion"
    __table_args__ = (
        UniqueConstraint(
            "fecha",
            "franja",
            "paciente_id",
            name="uq_ocupacion_fecha_franja_paciente",
        ),
        Index("ix_ocupacion_fecha_franja", "fecha", "franja"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    franja: Mapped[Franja] = mapped_column(_FRANJA_ENUM, nullable=False)
    reserva_id: Mapped[int] = mapped_column(ForeignKey("reserva.id"), nullable=False)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), nullable=False)


class HabilitacionEmergencia(Base):
    __tablename__ = "habilitacion_emergencia"
    __table_args__ = (
        CheckConstraint("trim(motivo) != ''", name="motivo_no_vacio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    franja: Mapped[Franja] = mapped_column(_FRANJA_ENUM, nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    motivo: Mapped[str] = mapped_column(String(500), nullable=False)
    clave_idempotencia: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
