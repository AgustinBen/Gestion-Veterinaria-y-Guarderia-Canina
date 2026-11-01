"""Endpoints de consulta y operación de reservas y cupo de guardería."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.cobros import service as cobros_service
from app.modules.guarderia import service
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import EstadoReserva
from app.modules.guarderia.schemas import (
    Disponibilidad,
    HabilitacionEmergenciaCrear,
    ReservaCrear,
    ReservaOut,
    ReservaSenaCrear,
)
from app.modules.identidad.deps import require_acceso
from app.modules.identidad.permisos import Nivel, Recurso
from app.modules.identidad.schemas import UsuarioActual

router = APIRouter(prefix="/api/guarderia", tags=["guarderia"])


@router.get("/disponibilidad", response_model=Disponibilidad)
def disponibilidad(
    fecha: date,
    franja: Franja,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.RESERVAS_CUPO, Nivel.LECTURA)
    ),
) -> Disponibilidad:
    return service.disponibilidad(db, fecha, franja)


@router.get("/calendario", response_model=list[Disponibilidad])
def calendario(
    desde: date,
    hasta: date,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.RESERVAS_CUPO, Nivel.LECTURA)
    ),
) -> list[Disponibilidad]:
    try:
        return service.calendario(db, desde, hasta)
    except service.RangoCalendarioInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post("/emergencias", response_model=Disponibilidad)
def habilitar_emergencia(
    solicitud: HabilitacionEmergenciaCrear,
    clave_idempotencia: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=64,
    ),
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.EMERGENCIA, Nivel.ESCRITURA)
    ),
) -> Disponibilidad:
    try:
        return service.habilitar_plaza_emergencia(
            db,
            solicitud,
            clave_idempotencia=clave_idempotencia,
            usuario_id=usuario.id,
        )
    except service.IdempotenciaEmergenciaConflicto as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except service.CupoEmergenciaAgotado as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except service.ReservaInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def _error_cupo(exc: service.ReservaCupoConflicto) -> HTTPException:
    resultado = exc.resultado
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "codigo": resultado.codigo,
            "franjas_sin_lugar": [
                franja.model_dump(mode="json")
                for franja in resultado.franjas_sin_lugar
            ],
            "ocupaciones_existentes": [
                ocupacion.model_dump(mode="json")
                for ocupacion in resultado.ocupaciones_existentes
            ],
        },
    )


def _error_cobros(exc: cobros_service.CobrosError) -> HTTPException:
    if isinstance(exc, cobros_service.IdempotenciaConflicto):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"codigo": "IDEMPOTENCIA_CONFLICTO", "mensaje": str(exc)},
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


@router.post(
    "/reservas",
    response_model=ReservaOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_reserva(
    solicitud: ReservaCrear,
    response: Response,
    clave_idempotencia: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=64,
    ),
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.RESERVAS_CUPO, Nivel.ESCRITURA)
    ),
) -> ReservaOut:
    try:
        reserva, creada = service.crear_reserva(
            db,
            solicitud,
            clave_idempotencia=clave_idempotencia,
            usuario_id=usuario.id,
        )
    except service.ReservaCupoConflicto as exc:
        raise _error_cupo(exc) from exc
    except service.IdempotenciaReservaConflicto as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"codigo": "IDEMPOTENCIA_CONFLICTO", "mensaje": str(exc)},
        ) from exc
    except service.ReservaInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except cobros_service.CobrosError as exc:
        raise _error_cobros(exc) from exc
    if not creada:
        response.status_code = status.HTTP_200_OK
    return reserva


@router.post(
    "/reservas/{reserva_id}/sena",
    response_model=ReservaOut,
)
def registrar_sena(
    reserva_id: int,
    solicitud: ReservaSenaCrear,
    clave_idempotencia: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=64,
    ),
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.RESERVAS_CUPO, Nivel.ESCRITURA)
    ),
) -> ReservaOut:
    try:
        return service.registrar_sena(
            db,
            reserva_id,
            solicitud,
            clave_idempotencia=clave_idempotencia,
            usuario_id=usuario.id,
            empleado_id=usuario.empleado_id,
        )
    except service.ReservaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except service.EstadoReservaInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except service.ReservaInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except cobros_service.CargoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except cobros_service.CobrosError as exc:
        raise _error_cobros(exc) from exc


@router.get(
    "/reservas/{reserva_id}",
    response_model=ReservaOut,
)
def obtener_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.RESERVAS_CUPO, Nivel.LECTURA)
    ),
) -> ReservaOut:
    try:
        return service.obtener_reserva(db, reserva_id)
    except service.ReservaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/reservas/{reserva_id}/cancelar",
    response_model=ReservaOut,
)
def cancelar_reserva(
    reserva_id: int,
    clave_idempotencia: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=64,
    ),
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.RESERVAS_CUPO, Nivel.ESCRITURA)
    ),
) -> ReservaOut:
    try:
        return service.cancelar_reserva(
            db,
            reserva_id,
            clave_idempotencia=clave_idempotencia,
            usuario_id=usuario.id,
        )
    except service.ReservaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        service.EstadoReservaInvalido,
        service.IdempotenciaCancelacionConflicto,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except service.ReservaInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except cobros_service.CargoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except cobros_service.CobrosError as exc:
        raise _error_cobros(exc) from exc


@router.get("/reservas", response_model=list[ReservaOut])
def listar_reservas(
    desde: date | None = None,
    hasta: date | None = None,
    estado: EstadoReserva | None = None,
    persona_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.RESERVAS_CUPO, Nivel.LECTURA)
    ),
) -> list[ReservaOut]:
    try:
        return service.listar_reservas(
            db,
            desde=desde,
            hasta=hasta,
            estado=estado,
            persona_id=persona_id,
        )
    except service.RangoCalendarioInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
