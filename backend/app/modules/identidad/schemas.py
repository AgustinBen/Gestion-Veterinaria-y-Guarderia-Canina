"""Schemas del módulo identidad."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.modules.identidad.permisos import Rol


class UsuarioActual(BaseModel):
    """Usuario autenticado, tal como lo ven las dependencias."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    rol: Rol
    empleado_id: int | None = None
