"""Endpoints de solo lectura para el cupo de guardería."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.guarderia import service
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.schemas import Disponibilidad
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
