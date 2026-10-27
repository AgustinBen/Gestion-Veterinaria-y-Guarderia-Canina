"""Modelos del módulo padrón."""
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
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class TipoEmpleado(str, Enum):
    INTERNO = "INTERNO"
    EXTERNO = "EXTERNO"


class Persona(Base):
    __tablename__ = "persona"
    __table_args__ = (
        CheckConstraint("trim(nombre) != ''", name="ck_persona_nombre_no_vacio"),
        CheckConstraint("trim(apellido) != ''", name="ck_persona_apellido_no_vacio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    dni: Mapped[str | None] = mapped_column(String(10), unique=True, nullable=True)
    domicilio_id: Mapped[int | None] = mapped_column(
        ForeignKey("domicilio.id"), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    creado_por: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicado_confirmado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )


class Domicilio(Base):
    __tablename__ = "domicilio"

    id: Mapped[int] = mapped_column(primary_key=True)
    calle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    piso: Mapped[str | None] = mapped_column(String(10), nullable=True)
    departamento: Mapped[str | None] = mapped_column(String(10), nullable=True)
    localidad: Mapped[str | None] = mapped_column(String(60), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    referencia: Mapped[str | None] = mapped_column(String(150), nullable=True)


class Telefono(Base):
    __tablename__ = "telefono"
    __table_args__ = (
        UniqueConstraint(
            "persona_id", "numero_normalizado", name="uq_telefono_persona_numero"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    persona_id: Mapped[int] = mapped_column(
        ForeignKey("persona.id"), nullable=False
    )
    numero_normalizado: Mapped[str] = mapped_column(String(15), nullable=False)
    numero_original: Mapped[str] = mapped_column(String(30), nullable=False)


class Cliente(Base):
    __tablename__ = "cliente"

    persona_id: Mapped[int] = mapped_column(
        ForeignKey("persona.id"), primary_key=True
    )
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)


class Empleado(Base):
    __tablename__ = "empleado"

    persona_id: Mapped[int] = mapped_column(
        ForeignKey("persona.id"), primary_key=True
    )
    tipo: Mapped[TipoEmpleado] = mapped_column(
        SAEnum(
            TipoEmpleado,
            name="tipo_empleado",
            native_enum=False,
            length=20,
            create_constraint=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    es_veterinario: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    especialidad: Mapped[str | None] = mapped_column(String(45), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


class Especie(Base):
    __tablename__ = "especie"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)


class Raza(Base):
    __tablename__ = "raza"
    __table_args__ = (
        UniqueConstraint("especie_id", "nombre", name="uq_raza_especie_nombre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), nullable=False)
    especie_id: Mapped[int] = mapped_column(
        ForeignKey("especie.id"), nullable=False
    )


class Tamanio(Base):
    __tablename__ = "tamanio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)


class Paciente(Base):
    __tablename__ = "paciente"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    especie_id: Mapped[int] = mapped_column(
        ForeignKey("especie.id"), nullable=False
    )
    raza_id: Mapped[int | None] = mapped_column(
        ForeignKey("raza.id"), nullable=True
    )
    tamanio_id: Mapped[int | None] = mapped_column(
        ForeignKey("tamanio.id"), nullable=True
    )
    peso_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    fecha_nacimiento_aprox: Mapped[date | None] = mapped_column(Date, nullable=True)
    castrado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


class TipoContacto(Base):
    __tablename__ = "tipo_contacto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)


class Titularidad(Base):
    __tablename__ = "titularidad"
    __table_args__ = (
        Index(
            "ix_titularidad_unica_principal_vigente",
            "paciente_id",
            unique=True,
            sqlite_where=text("principal = 1 AND hasta IS NULL"),
        ),
        CheckConstraint("hasta IS NULL OR hasta >= desde", name="ck_titularidad_hasta_desde"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("paciente.id"), nullable=False
    )
    persona_id: Mapped[int] = mapped_column(
        ForeignKey("persona.id"), nullable=False
    )
    tipo_contacto_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_contacto.id"), nullable=False
    )
    principal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
