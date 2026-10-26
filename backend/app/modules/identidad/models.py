"""Modelos del módulo identidad."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.modules.identidad.permisos import Rol


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[Rol] = mapped_column(
        Enum(
            Rol,
            name="rol_usuario",
            native_enum=False,
            length=20,
            create_constraint=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    empleado_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
