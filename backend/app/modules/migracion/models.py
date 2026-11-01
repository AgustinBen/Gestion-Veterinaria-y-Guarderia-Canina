"""Registro de las filas migradas: idempotencia y trazabilidad (T-16, RN-50)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base

HOJA_CLIENTES = "Clientes_y_Mascotas"

ESTADO_CARGADA = "CARGADA"
ESTADO_REVISION = "REVISION"
ESTADO_ERROR = "ERROR"


class EstadoMigracion(str, Enum):
    CARGADA = ESTADO_CARGADA
    REVISION = ESTADO_REVISION
    ERROR = ESTADO_ERROR


class MigracionRegistro(Base):
    """Una fila del Excel y qué pasó con ella en la última corrida."""

    __tablename__ = "migracion_registro"
    __table_args__ = (
        UniqueConstraint("hoja", "fila", name="uq_migracion_registro_hoja_fila"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hoja: Mapped[str] = mapped_column(String(60), nullable=False)
    fila: Mapped[int] = mapped_column(Integer, nullable=False)
    id_origen: Mapped[str | None] = mapped_column(String(60), nullable=True)
    hash_fila: Mapped[str] = mapped_column(String(64), nullable=False)
    texto_original: Mapped[str] = mapped_column(Text, nullable=False)
    entidad: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entidad_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origen_confirmacion: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
