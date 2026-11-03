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
egresos_router = APIRouter(prefix="/api", tags=["panel"])


def _leer_finanzas() -> Callable[..., UsuarioActual]:
    return require_acceso(Recurso.FINANZAS, Nivel.LECTURA)


def _escribir_finanzas() -> Callable[..., UsuarioActual]:
    return require_acceso(Recurso.FINANZAS, Nivel.ESCRITURA)


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


@egresos_router.get(
    "/categorias-egreso", response_model=list[schemas.CategoriaEgresoOut]
)
def listar_categorias_egreso(
    activa: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> list[schemas.CategoriaEgresoOut]:
    return service.listar_categorias_egreso(db, activa=activa)


@egresos_router.post(
    "/categorias-egreso",
    response_model=schemas.CategoriaEgresoOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_categoria_egreso(
    datos: schemas.CategoriaEgresoCrear,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_escribir_finanzas()),
) -> schemas.CategoriaEgresoOut:
    try:
        return service.crear_categoria_egreso(db, datos)
    except service.CategoriaDuplicada as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except service.DatosInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@egresos_router.patch(
    "/categorias-egreso/{categoria_id}",
    response_model=schemas.CategoriaEgresoOut,
)
def actualizar_categoria_egreso(
    categoria_id: int,
    datos: schemas.CategoriaEgresoActualizar,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_escribir_finanzas()),
) -> schemas.CategoriaEgresoOut:
    try:
        return service.actualizar_categoria_egreso(db, categoria_id, datos)
    except service.CategoriaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@egresos_router.post(
    "/egresos",
    response_model=schemas.EgresoOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_egreso(
    datos: schemas.EgresoCrear,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(_escribir_finanzas()),
) -> schemas.EgresoOut:
    try:
        return service.crear_egreso(db, datos, usuario_id=usuario.id)
    except service.DatosInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@egresos_router.get("/egresos", response_model=list[schemas.EgresoOut])
def listar_egresos(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    categoria_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> list[schemas.EgresoOut]:
    try:
        return service.listar_egresos(
            db, desde=desde, hasta=hasta, categoria_id=categoria_id
        )
    except service.PeriodoInvalido as exc:
        raise _periodo_invalido(exc) from exc


@egresos_router.post(
    "/egresos/{egreso_id}/anular", response_model=schemas.EgresoOut
)
def anular_egreso(
    egreso_id: int,
    datos: schemas.EgresoAnular,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(_escribir_finanzas()),
) -> schemas.EgresoOut:
    try:
        return service.anular_egreso(
            db, egreso_id, motivo=datos.motivo, usuario_id=usuario.id
        )
    except service.EgresoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except service.EgresoYaAnulado as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except service.DatosInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
