"""Modelos de historia clínica, separados de los cargos y pagos."""

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


class TipoAtencion(str, Enum):
    CONSULTA = "CONSULTA"
    VACUNA = "VACUNA"
    CIRUGIA = "CIRUGIA"
    TRATAMIENTO = "TRATAMIENTO"
    ESTUDIO = "ESTUDIO"


class OrigenAtencion(str, Enum):
    NORMAL = "NORMAL"
    MIGRACION = "MIGRACION"


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
    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("paciente.id"), nullable=False
    )
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
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
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
    cargo_id: Mapped[int | None] = mapped_column(
        ForeignKey("cargo.id"), nullable=True
    )
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
    rectifica_a_id: Mapped[int | None] = mapped_column(
        ForeignKey("atencion.id"), nullable=True
    )
    rectificada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("usuario.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VacunaAplicada(Base):
    __tablename__ = "vacuna_aplicada"
    __table_args__ = (
        UniqueConstraint("atencion_id", name="uq_vacuna_aplicada_atencion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atencion_id: Mapped[int] = mapped_column(
        ForeignKey("atencion.id"), nullable=False
    )
    nombre_vacuna: Mapped[str] = mapped_column(String(100), nullable=False)
    lote: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_aplicacion: Mapped[date] = mapped_column(Date, nullable=False)
    proxima_dosis: Mapped[date | None] = mapped_column(Date, nullable=True)
