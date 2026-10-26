"""Endpoints del módulo identidad."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identidad import service
from app.modules.identidad.deps import get_current_user, require_role
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import (
    ConfiguracionItem,
    ConfiguracionUpdate,
    LoginRequest,
    LoginResponse,
    UsuarioActual,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioPublico,
)

router = APIRouter(prefix="/api", tags=["identidad"])


def _credenciales_invalidas() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/auth/login", response_model=LoginResponse)
def login(
    datos: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    try:
        return service.login(db, datos.username, datos.password)
    except service.CredencialesInvalidas as exc:
        raise _credenciales_invalidas() from exc


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    _usuario: UsuarioActual = Depends(get_current_user),
) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/auth/me", response_model=UsuarioActual)
def me(
    usuario: UsuarioActual = Depends(get_current_user),
) -> UsuarioActual:
    return usuario


@router.get("/usuarios", response_model=list[UsuarioPublico])
def listar_usuarios(
    db: Session = Depends(get_db),
    _actor: UsuarioActual = Depends(require_role(Rol.DUENIO)),
) -> list[UsuarioPublico]:
    return service.listar_usuarios(db)


@router.post(
    "/usuarios",
    response_model=UsuarioPublico,
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario(
    datos: UsuarioCrear,
    db: Session = Depends(get_db),
    _actor: UsuarioActual = Depends(require_role(Rol.DUENIO)),
) -> UsuarioPublico:
    try:
        return service.crear_usuario(db, datos)
    except service.DatosInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except service.UsernameDuplicado as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El username ya está registrado",
        ) from exc


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioPublico)
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioActualizar,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_role(Rol.DUENIO)),
) -> UsuarioPublico:
    try:
        return service.actualizar_usuario(db, usuario_id, datos, actor)
    except service.DatosInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except service.UsuarioNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        ) from exc
    except service.OperacionNoPermitida as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/config", response_model=list[ConfiguracionItem])
def listar_configuracion(
    db: Session = Depends(get_db),
    _actor: UsuarioActual = Depends(require_role(Rol.DUENIO)),
) -> list[ConfiguracionItem]:
    return service.listar_configuracion(db)


@router.put("/config/{clave}", response_model=ConfiguracionItem)
def actualizar_configuracion(
    clave: str,
    datos: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_role(Rol.DUENIO)),
) -> ConfiguracionItem:
    try:
        return service.actualizar_configuracion(db, clave, datos, actor)
    except service.ConfiguracionNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración no encontrada",
        ) from exc
    except service.DatosInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
