"""Schemas del módulo identidad."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.identidad.permisos import Rol


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class LoginResponse(BaseModel):
    """Token emitido al iniciar sesión."""

    access_token: str
    token_type: str = "bearer"
    rol: Rol


class UsuarioActual(BaseModel):
    """Usuario autenticado, tal como lo ven las dependencias."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    rol: Rol
    empleado_id: int | None = None


class UsuarioCrear(BaseModel):
    """Datos para crear un usuario."""

    model_config = ConfigDict(extra="forbid")

    username: str
    password: str
    rol: Rol
    empleado_id: int | None = None


class UsuarioActualizar(BaseModel):
    """Cambios parciales de un usuario. Los campos omitidos no se tocan."""

    model_config = ConfigDict(extra="forbid")

    activo: bool | None = None
    rol: Rol | None = None
    password: str | None = None


class UsuarioPublico(BaseModel):
    """Usuario sin datos sensibles."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    rol: Rol
    activo: bool
    empleado_id: int | None
    creado_en: datetime


class ConfiguracionItem(BaseModel):
    """Parámetro de configuración con su valor crudo y su tipo."""

    model_config = ConfigDict(from_attributes=True)

    clave: str
    valor: str
    tipo: str
    modulo: str | None
    descripcion: str | None
    updated_by: str | None
    updated_at: datetime


class ConfiguracionUpdate(BaseModel):
    """Nuevo valor de un parámetro existente. El tipo lo define la base."""

    model_config = ConfigDict(extra="forbid")

    valor: str | int | float | bool
