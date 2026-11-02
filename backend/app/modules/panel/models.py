"""Modelos del módulo panel.

Incluye lo mínimo de T-38 (egresos operativos) que necesita el panel
financiero de T-46: categorías y egresos con anulación auditada.
El dinero se guarda en centavos como INTEGER.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class CategoriaEgreso(Base):
    __tablename__ = "categoria_egreso"
    __table_args__ = (
        CheckConstraint("trim(nombre) <> ''", name="ck_categoria_egreso_nombre_no_vacio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(
        String(80), nullable=False, unique=True
    )
    activa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


class Egreso(Base):
    __tablename__ = "egreso"
    __table_args__ = (
        CheckConstraint("monto_centavos > 0", name="ck_egreso_monto_positivo"),
        CheckConstraint("typeof(monto_centavos) = 'integer'", name="ck_egreso_monto_entero"),
        Index("ix_egreso_fecha", "fecha"),
        Index("ix_egreso_categoria_id", "categoria_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categoria_egreso.id"), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    medio_pago_id: Mapped[int | None] = mapped_column(
        ForeignKey("medio_pago.id"), nullable=True
    )
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    anulado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anulado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
