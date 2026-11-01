"""Endpoints de historia clínica y libreta de vacunas."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.clinica import service
from app.modules.clinica.models import TipoAtencion
from app.modules.clinica.schemas import (
    AtencionCrear,
    AtencionDetalle,
    AtencionResumen,
    LibretaVacunasItem,
)
from app.modules.identidad.deps import require_acceso
from app.modules.identidad.permisos import Nivel, Recurso
from app.modules.identidad.schemas import UsuarioActual

router = APIRouter(tags=["clinica"])


def _error_datos_invalidos(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


@router.post(
    "/api/pacientes/{paciente_id}/atenciones",
    response_model=AtencionDetalle,
    status_code=status.HTTP_201_CREATED,
)
def crear_atencion(
    paciente_id: int,
    solicitud: AtencionCrear,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.HISTORIA_CLINICA, Nivel.ESCRITURA)
    ),
) -> AtencionDetalle:
    try:
        return service.registrar_atencion(
            db,
            paciente_id,
            solicitud,
            created_by=usuario.id,
            empleado_por_defecto=usuario.empleado_id,
        )
    except service.PacienteNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        ) from exc
    except (service.EmpleadoNoEncontrado, service.DatosInvalidos) as exc:
        raise _error_datos_invalidos(exc) from exc


@router.get(
    "/api/pacientes/{paciente_id}/atenciones",
    response_model=list[AtencionResumen],
)
def listar_atenciones(
    paciente_id: int,
    tipo: TipoAtencion | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.HISTORIA_CLINICA, Nivel.LECTURA)
    ),
) -> list[AtencionResumen]:
    try:
        return service.atenciones_de_paciente(
            db,
            paciente_id,
            tipo=tipo,
            desde=desde,
            hasta=hasta,
            limit=limit,
            offset=offset,
        )
    except service.PacienteNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        ) from exc
    except (service.DatosInvalidos, service.RangoFechasInvalido) as exc:
        raise _error_datos_invalidos(exc) from exc


@router.get(
    "/api/atenciones/{atencion_id}",
    response_model=AtencionDetalle,
)
def obtener_atencion(
    atencion_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.HISTORIA_CLINICA, Nivel.LECTURA)
    ),
) -> AtencionDetalle:
    try:
        return service.obtener_atencion(db, atencion_id)
    except service.AtencionNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atención no encontrada",
        ) from exc


@router.post(
    "/api/atenciones/{atencion_id}/rectificar",
    response_model=AtencionDetalle,
    status_code=status.HTTP_201_CREATED,
)
def rectificar_atencion(
    atencion_id: int,
    solicitud: AtencionCrear,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.HISTORIA_CLINICA, Nivel.ESCRITURA)
    ),
) -> AtencionDetalle:
    try:
        return service.rectificar_atencion(
            db,
            atencion_id,
            solicitud,
            created_by=usuario.id,
            empleado_por_defecto=usuario.empleado_id,
        )
    except service.AtencionNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atención no encontrada",
        ) from exc
    except (
        service.PacienteNoEncontrado,
        service.EmpleadoNoEncontrado,
        service.DatosInvalidos,
    ) as exc:
        raise _error_datos_invalidos(exc) from exc


@router.get(
    "/api/pacientes/{paciente_id}/libreta-vacunas",
    response_model=list[LibretaVacunasItem],
)
def libreta_vacunas(
    paciente_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.HISTORIA_CLINICA, Nivel.LECTURA)
    ),
) -> list[LibretaVacunasItem]:
    try:
        return service.libreta_vacunas(db, paciente_id)
    except service.PacienteNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        ) from exc
