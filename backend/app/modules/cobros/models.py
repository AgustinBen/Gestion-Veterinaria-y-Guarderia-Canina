"""Modelos del módulo cobros.

Dinero siempre en centavos como INTEGER. Sin columnas saldo/deuda.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class OrigenCargo(str, Enum):
    NORMAL = "NORMAL"
    MIGRACION = "MIGRACION"


class TipoPago(str, Enum):
    PAGO = "PAGO"
    REVERSO = "REVERSO"


class MedioPago(Base):
    __tablename__ = "medio_pago"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class Cargo(Base):
    __tablename__ = "cargo"
    __table_args__ = (
        CheckConstraint("total_inicial > 0", name="ck_cargo_total_inicial_positivo"),
        CheckConstraint(
            "typeof(total_inicial) = 'integer'",
            name="ck_cargo_total_inicial_entero",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("persona.id"), nullable=False)
    paciente_id: Mapped[int | None] = mapped_column(ForeignKey("paciente.id"), nullable=True)
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    total_inicial: Mapped[int] = mapped_column(Integer, nullable=False)
    origen: Mapped[OrigenCargo] = mapped_column(
        SAEnum(OrigenCargo, name="origen_cargo", native_enum=False, length=20, create_constraint=False, validate_strings=True),
        nullable=False,
        default=OrigenCargo.NORMAL,
        server_default="NORMAL",
    )
    texto_original: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referencia_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referencia_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AjustePrecio(Base):
    __tablename__ = "ajuste_precio"
    __table_args__ = (
        CheckConstraint(
            "precio_nuevo >= 0",
            name="ck_ajuste_precio_nuevo_no_negativo",
        ),
        CheckConstraint(
            "typeof(precio_anterior) = 'integer' AND typeof(precio_nuevo) = 'integer'",
            name="ck_ajuste_precio_importes_enteros",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cargo_id: Mapped[int] = mapped_column(ForeignKey("cargo.id"), nullable=False)
    precio_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_nuevo: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Pago(Base):
    __tablename__ = "pago"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_pago_monto_positivo"),
        CheckConstraint("typeof(monto) = 'integer'", name="ck_pago_monto_entero"),
        CheckConstraint(
            "(tipo = 'REVERSO' AND pago_revertido_id IS NOT NULL) "
            "OR (tipo = 'PAGO' AND pago_revertido_id IS NULL)",
            name="ck_pago_referencia_reverso",
        ),
        Index("ix_pago_cargo_id", "cargo_id"),
        Index("ix_pago_fecha", "fecha"),
        UniqueConstraint("id", "cargo_id", name="uq_pago_id_cargo"),
        ForeignKeyConstraint(
            ["pago_revertido_id", "cargo_id"],
            ["pago.id", "pago.cargo_id"],
            name="fk_pago_revertido_mismo_cargo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cargo_id: Mapped[int] = mapped_column(ForeignKey("cargo.id"), nullable=False)
    monto: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[TipoPago] = mapped_column(
        SAEnum(TipoPago, name="tipo_pago", native_enum=False, length=20, create_constraint=False, validate_strings=True),
        nullable=False,
    )
    pago_revertido_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    medio_pago_id: Mapped[int] = mapped_column(ForeignKey("medio_pago.id"), nullable=False)
    es_sena: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    empleado_id: Mapped[int | None] = mapped_column(
        ForeignKey("empleado.persona_id"), nullable=True
    )
    clave_idempotencia: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Solo se usa en reversos: por qué se revirtió el pago.
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ServicioPrestado(Base):
    __tablename__ = "servicio_prestado"

    id: Mapped[int] = mapped_column(primary_key=True)
    cargo_id: Mapped[int] = mapped_column(ForeignKey("cargo.id"), nullable=False)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.persona_id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)


class GastoExterno(Base):
    __tablename__ = "gasto_externo"
    __table_args__ = (
        CheckConstraint(
            "typeof(monto) = 'integer' AND monto >= 0",
            name="ck_gasto_externo_monto_entero_no_negativo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.persona_id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    monto: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    cargo_id: Mapped[int | None] = mapped_column(ForeignKey("cargo.id"), nullable=True)
    pago_id: Mapped[int | None] = mapped_column(ForeignKey("pago.id"), nullable=True)
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)


# Índice único parcial para clave_idempotencia (solo donde no es NULL)
Index("uq_pago_clave_idempotencia", Pago.clave_idempotencia, unique=True, sqlite_where=Pago.clave_idempotencia.isnot(None))
Index("ix_cargo_persona_id", Cargo.persona_id)
Index("ix_cargo_paciente_id", Cargo.paciente_id)
Index("ix_servicio_prestado_cargo_id", ServicioPrestado.cargo_id)
Index("ix_gasto_externo_cargo_id", GastoExterno.cargo_id)
Index("ix_gasto_externo_pago_id", GastoExterno.pago_id)
Index("ix_ajuste_precio_cargo_id", AjustePrecio.cargo_id)
