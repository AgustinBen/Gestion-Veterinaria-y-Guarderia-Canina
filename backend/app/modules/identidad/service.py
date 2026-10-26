"""Reglas de negocio del módulo identidad."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.identidad import repository, security
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioActual


class NoAutenticado(Exception):
    """Credenciales inválidas, token inválido/vencido o usuario inactivo."""


def usuario_actual(db: Session, token: str) -> UsuarioActual:
    """Resuelve el usuario autenticado consultando estado y rol en la base.

    La consulta a la base se hace en cada pedido: un usuario desactivado no
    sigue autenticado aunque su token siga vigente.
    """
    try:
        payload = security.decodificar_token(token)
    except security.TokenInvalido as exc:
        raise NoAutenticado("No autenticado") from exc

    usuario = repository.obtener_por_id(db, payload.usuario_id)
    if usuario is None or not usuario.activo:
        raise NoAutenticado("No autenticado")

    return UsuarioActual.model_validate(usuario)


def tiene_rol(usuario: UsuarioActual, *roles: Rol) -> bool:
    """Indica si el usuario tiene alguno de los roles. Sin roles: deniega."""
    return usuario.rol in roles
