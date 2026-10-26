"""Dependencias de autenticación y autorización del módulo identidad."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identidad import permisos, service
from app.modules.identidad.permisos import Nivel, Recurso, Rol
from app.modules.identidad.schemas import UsuarioActual

_bearer = HTTPBearer(auto_error=False)


def _no_autenticado() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> UsuarioActual:
    """Devuelve el usuario autenticado o 401 con la misma respuesta siempre."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _no_autenticado()

    try:
        return service.usuario_actual(db, credentials.credentials)
    except service.NoAutenticado as exc:
        raise _no_autenticado() from exc


def require_role(*roles: Rol) -> Callable[..., UsuarioActual]:
    """Exige que el usuario tenga alguno de los roles. Sin roles: deniega."""

    def _dependencia(
        usuario: UsuarioActual = Depends(get_current_user),
    ) -> UsuarioActual:
        if not service.tiene_rol(usuario, *roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado",
            )
        return usuario

    return _dependencia


def require_acceso(
    recurso: Recurso, nivel: Nivel = Nivel.LECTURA
) -> Callable[..., UsuarioActual]:
    """Exige el nivel indicado para el recurso según la matriz de permisos."""

    def _dependencia(
        usuario: UsuarioActual = Depends(get_current_user),
    ) -> UsuarioActual:
        if not permisos.puede(usuario.rol, recurso, nivel):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado",
            )
        return usuario

    return _dependencia
