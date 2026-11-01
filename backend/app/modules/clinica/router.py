"""Endpoints de historia clínica y libreta de vacunas."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.modules.clinica import almacenamiento, service
from app.modules.clinica.models import TipoAtencion
from app.modules.clinica.schemas import (
    AdjuntoResumen,
    AtencionCrear,
    AtencionDetalle,
    AtencionResumen,
    EstudioCrear,
    EstudioResumen,
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
    usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.ESCRITURA)),
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
    _usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.LECTURA)),
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
    _usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.LECTURA)),
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
    usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.ESCRITURA)),
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
    _usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.LECTURA)),
) -> list[LibretaVacunasItem]:
    try:
        return service.libreta_vacunas(db, paciente_id)
    except service.PacienteNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        ) from exc


@router.post(
    "/api/pacientes/{paciente_id}/estudios",
    response_model=EstudioResumen,
    status_code=status.HTTP_201_CREATED,
)
def registrar_estudio(
    paciente_id: int,
    solicitud: EstudioCrear,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.ESCRITURA)),
) -> EstudioResumen:
    try:
        return service.registrar_estudio(
            db,
            paciente_id,
            solicitud,
            created_by=usuario.id,
        )
    except service.PacienteNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        ) from exc
    except (service.EmpleadoNoEncontrado, service.DatosInvalidos) as exc:
        raise _error_datos_invalidos(exc) from exc


@router.get(
    "/api/pacientes/{paciente_id}/estudios",
    response_model=list[EstudioResumen],
)
def listar_estudios(
    paciente_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.LECTURA)),
) -> list[EstudioResumen]:
    try:
        return service.listar_estudios(db, paciente_id)
    except service.PacienteNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        ) from exc


@router.post(
    "/api/estudios/{estudio_id}/adjuntos",
    response_model=AdjuntoResumen,
    status_code=status.HTTP_201_CREATED,
)
def subir_adjunto(
    estudio_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.ESCRITURA)),
) -> AdjuntoResumen:
    try:
        service.verificar_estudio(db, estudio_id)
    except service.EstudioNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudio no encontrado",
        ) from exc

    settings = get_settings()
    nombre_original = archivo.filename or "archivo"
    try:
        almacenado = almacenamiento.guardar(
            archivo.file,
            Path(settings.uploads_dir),
            max_bytes=settings.upload_max_bytes,
            tipos_permitidos=set(settings.upload_allowed_mime_types),
        )
    except almacenamiento.ArchivoDemasiadoGrande as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="El archivo supera el tamaño máximo permitido",
        ) from exc
    except almacenamiento.TipoArchivoNoPermitido as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El contenido del archivo no es de un tipo permitido",
        ) from exc

    try:
        return service.registrar_adjunto(
            db,
            estudio_id,
            almacenado,
            nombre_original=nombre_original,
            created_by=usuario.id,
        )
    except service.EstudioNoEncontrado as exc:
        almacenamiento.eliminar(almacenado.ruta)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudio no encontrado",
        ) from exc


@router.get("/api/adjuntos/{adjunto_id}/archivo")
def descargar_adjunto(
    adjunto_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(require_acceso(Recurso.HISTORIA_CLINICA, Nivel.LECTURA)),
) -> FileResponse:
    try:
        adjunto = service.obtener_adjunto_para_descarga(db, adjunto_id)
    except service.AdjuntoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adjunto no encontrado",
        ) from exc

    ruta = almacenamiento.ruta_archivo(Path(get_settings().uploads_dir), adjunto.nombre_archivo)
    if not ruta.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado",
        )
    disposition = quote(adjunto.nombre_original, safe="")
    return FileResponse(
        ruta,
        media_type=adjunto.tipo_mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{disposition}",
            "X-Content-Type-Options": "nosniff",
        },
    )
