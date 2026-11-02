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
    Response,
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
    AgendaDiaOut,
    AtencionCrear,
    AtencionDetalle,
    AtencionResumen,
    EstudioCrear,
    EstudioResumen,
    HorarioAtencionIn,
    HorarioAtencionOut,
    LibretaVacunasItem,
    TurnoAtendido,
    TurnoCancelar,
    TurnoCrear,
    TurnoOut,
    TurnoPersonalIn,
    TurnoPersonalOut,
    TurnoReprogramar,
    TurnosPersonalDefinicionIn,
    TurnosPersonalDefinicionOut,
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


def _error_agenda(exc: service.AgendaError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"codigo": exc.codigo, "mensaje": str(exc)},
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


@router.get(
    "/api/clinica/horarios",
    response_model=list[HorarioAtencionOut],
)
def obtener_horarios(
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.LECTURA)
    ),
) -> list[HorarioAtencionOut]:
    return service.horarios_atencion(db)


@router.put(
    "/api/clinica/horarios",
    response_model=list[HorarioAtencionOut],
)
def actualizar_horarios(
    solicitud: list[HorarioAtencionIn],
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.USUARIOS_CONFIG, Nivel.ESCRITURA)
    ),
) -> list[HorarioAtencionOut]:
    try:
        return service.reemplazar_horarios_atencion(db, solicitud)
    except ValueError as exc:
        raise _error_datos_invalidos(exc) from exc


@router.get(
    "/api/clinica/turnos-personal/definicion",
    response_model=TurnosPersonalDefinicionOut,
)
def obtener_definicion_turnos_personal(
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.LECTURA)
    ),
) -> TurnosPersonalDefinicionOut:
    return service.definicion_turnos_personal(db)


@router.put(
    "/api/clinica/turnos-personal/definicion",
    response_model=TurnosPersonalDefinicionOut,
)
def actualizar_definicion_turnos_personal(
    solicitud: TurnosPersonalDefinicionIn,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.USUARIOS_CONFIG, Nivel.ESCRITURA)
    ),
) -> TurnosPersonalDefinicionOut:
    return service.reemplazar_definicion_turnos_personal(db, solicitud.turnos)


@router.post(
    "/api/clinica/turnos-personal",
    response_model=TurnoPersonalOut,
    status_code=status.HTTP_201_CREATED,
)
def asignar_turno_personal(
    solicitud: TurnoPersonalIn,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.USUARIOS_CONFIG, Nivel.ESCRITURA)
    ),
) -> TurnoPersonalOut:
    try:
        return service.asignar_turno_personal(db, solicitud)
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.get(
    "/api/clinica/turnos-personal",
    response_model=list[TurnoPersonalOut],
)
def listar_turnos_personal(
    desde: date | None = None,
    hasta: date | None = None,
    empleado_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.LECTURA)
    ),
) -> list[TurnoPersonalOut]:
    try:
        return service.turnos_personal(
            db, desde=desde, hasta=hasta, empleado_id=empleado_id
        )
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.delete(
    "/api/clinica/turnos-personal",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_turno_personal(
    empleado_id: int = Query(gt=0),
    fecha: date = Query(),
    turno: str = Query(),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.USUARIOS_CONFIG, Nivel.ESCRITURA)
    ),
) -> Response:
    from app.modules.clinica.models import FranjaTurnoPersonal

    try:
        tipo_turno = FranjaTurnoPersonal(turno)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Turno de personal inválido",
        ) from exc
    try:
        service.quitar_turno_personal(
            db,
            TurnoPersonalIn(
                empleado_id=empleado_id,
                fecha=fecha,
                turno=tipo_turno,
            ),
        )
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api/turnos",
    response_model=TurnoOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_turno(
    solicitud: TurnoCrear,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.ESCRITURA)
    ),
) -> TurnoOut:
    try:
        return service.agendar_turno(db, solicitud, created_by=usuario.id)
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.get("/api/turnos", response_model=list[TurnoOut])
def listar_turnos(
    desde: date | None = None,
    hasta: date | None = None,
    veterinario_id: int | None = Query(default=None, gt=0),
    paciente_id: int | None = Query(default=None, gt=0),
    estado: str | None = None,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.LECTURA)
    ),
) -> list[TurnoOut]:
    from app.modules.clinica.models import EstadoTurno

    try:
        estado_turno = EstadoTurno(estado) if estado is not None else None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Estado de turno inválido",
        ) from exc
    try:
        return service.listar_turnos(
            db,
            desde=desde,
            hasta=hasta,
            veterinario_id=veterinario_id,
            paciente_id=paciente_id,
            estado=estado_turno,
        )
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.get("/api/turnos/{turno_id}", response_model=TurnoOut)
def obtener_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.LECTURA)
    ),
) -> TurnoOut:
    try:
        return service.obtener_turno(db, turno_id)
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.patch("/api/turnos/{turno_id}", response_model=TurnoOut)
def reprogramar_turno(
    turno_id: int,
    solicitud: TurnoReprogramar,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.ESCRITURA)
    ),
) -> TurnoOut:
    try:
        return service.reprogramar_turno(db, turno_id, solicitud)
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.post("/api/turnos/{turno_id}/cancelar", response_model=TurnoOut)
def cancelar_turno(
    turno_id: int,
    solicitud: TurnoCancelar,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.ESCRITURA)
    ),
) -> TurnoOut:
    try:
        return service.cancelar_turno(db, turno_id, solicitud.motivo)
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.post("/api/turnos/{turno_id}/ausente", response_model=TurnoOut)
def marcar_turno_ausente(
    turno_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.ESCRITURA)
    ),
) -> TurnoOut:
    try:
        return service.marcar_turno_ausente(db, turno_id)
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.post("/api/turnos/{turno_id}/atendido", response_model=TurnoOut)
def marcar_turno_atendido(
    turno_id: int,
    solicitud: TurnoAtendido | None = None,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.ESCRITURA)
    ),
) -> TurnoOut:
    try:
        return service.marcar_turno_atendido(
            db, turno_id, solicitud.atencion_id if solicitud is not None else None
        )
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc


@router.get("/api/clinica/agenda", response_model=list[AgendaDiaOut])
def agenda(
    desde: date,
    hasta: date,
    veterinario_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(
        require_acceso(Recurso.TURNOS, Nivel.LECTURA)
    ),
) -> list[AgendaDiaOut]:
    try:
        return service.agenda(db, desde, hasta, veterinario_id)
    except service.AgendaError as exc:
        raise _error_agenda(exc) from exc
