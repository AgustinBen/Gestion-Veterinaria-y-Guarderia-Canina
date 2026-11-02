"""Endpoints del panel financiero del Dueño (T-46).

Todos son de solo lectura y exigen el recurso `finanzas`: PERSONAL y
VETERINARIO reciben 403 (RN-40).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.cobros import service as cobros_service
from app.modules.identidad.deps import require_acceso
from app.modules.identidad.permisos import Nivel, Recurso
from app.modules.identidad.schemas import UsuarioActual
from app.modules.panel import schemas, service

router = APIRouter(prefix="/api/panel", tags=["panel"])


def _leer_finanzas() -> Callable[..., UsuarioActual]:
    return require_acceso(Recurso.FINANZAS, Nivel.LECTURA)


def _periodo_invalido(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
    )


@router.get("/resumen", response_model=schemas.ResumenPanelOut)
def resumen(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    servicio: str | None = Query(default=None),
    medio: str | None = Query(default=None),
    incluir_migracion: bool = Query(default=False),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> schemas.ResumenPanelOut:
    try:
        return service.resumen(
            db,
            desde=desde,
            hasta=hasta,
            servicio=servicio,
            medio=medio,
            incluir_migracion=incluir_migracion,
        )
    except service.PeriodoInvalido as exc:
        raise _periodo_invalido(exc) from exc
    except cobros_service.CobrosError as exc:
        raise _periodo_invalido(exc) from exc


@router.get("/serie", response_model=schemas.SeriePanelOut)
def serie(
    agrupar: str = Query(default="dia"),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    servicio: str | None = Query(default=None),
    medio: str | None = Query(default=None),
    incluir_migracion: bool = Query(default=False),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> schemas.SeriePanelOut:
    try:
        return service.serie(
            db,
            desde=desde,
            hasta=hasta,
            agrupar=agrupar,
            servicio=servicio,
            medio=medio,
            incluir_migracion=incluir_migracion,
        )
    except service.PeriodoInvalido as exc:
        raise _periodo_invalido(exc) from exc
    except cobros_service.CobrosError as exc:
        raise _periodo_invalido(exc) from exc


@router.get("/ingresos-por-servicio", response_model=list[schemas.IngresoPorServicioOut])
def ingresos_por_servicio(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    servicio: str | None = Query(default=None),
    medio: str | None = Query(default=None),
    incluir_migracion: bool = Query(default=False),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> list[schemas.IngresoPorServicioOut]:
    try:
        return service.ingresos_por_servicio(
            db,
            desde=desde,
            hasta=hasta,
            servicio=servicio,
            medio=medio,
            incluir_migracion=incluir_migracion,
        )
    except service.PeriodoInvalido as exc:
        raise _periodo_invalido(exc) from exc
    except cobros_service.CobrosError as exc:
        raise _periodo_invalido(exc) from exc


@router.get("/ingresos-por-medio", response_model=list[schemas.IngresoPorMedioOut])
def ingresos_por_medio(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    servicio: str | None = Query(default=None),
    medio: str | None = Query(default=None),
    incluir_migracion: bool = Query(default=False),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> list[schemas.IngresoPorMedioOut]:
    try:
        return service.ingresos_por_medio(
            db,
            desde=desde,
            hasta=hasta,
            servicio=servicio,
            medio=medio,
            incluir_migracion=incluir_migracion,
        )
    except service.PeriodoInvalido as exc:
        raise _periodo_invalido(exc) from exc
    except cobros_service.CobrosError as exc:
        raise _periodo_invalido(exc) from exc


@router.get("/deudas", response_model=schemas.DeudasPanelOut)
def deudas(
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> schemas.DeudasPanelOut:
    return service.deudas(db)


@router.get(
    "/clientes/{persona_id}/servicios",
    response_model=schemas.DetalleClienteOut,
)
def detalle_cliente(
    persona_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> schemas.DetalleClienteOut:
    try:
        return service.detalle_cliente(db, persona_id)
    except service.PersonaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
