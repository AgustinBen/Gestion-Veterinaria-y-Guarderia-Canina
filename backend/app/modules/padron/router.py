"""Endpoints del módulo padrón."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identidad.deps import require_acceso, require_role
from app.modules.identidad.permisos import Nivel, Recurso, Rol
from app.modules.identidad.schemas import UsuarioActual
from app.modules.padron import schemas, service

router = APIRouter(prefix="/api", tags=["padron"])

_DUENIO = require_role(Rol.DUENIO)


def _leer() -> Callable[..., UsuarioActual]:
    return require_acceso(Recurso.PADRON, Nivel.LECTURA)


def _escribir() -> Callable[..., UsuarioActual]:
    return require_acceso(Recurso.PADRON, Nivel.ESCRITURA)


def _dni_duplicado(exc: service.DniDuplicado) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"codigo": "DNI_DUPLICADO", "persona": exc.persona.model_dump()},
    )


def _posible_duplicado(exc: service.PosibleDuplicado) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "codigo": "POSIBLE_DUPLICADO",
            "coincidencias": [
                coincidencia.model_dump() for coincidencia in exc.coincidencias
            ],
        },
    )


def _datos_invalidos(exc: service.DatosInvalidos) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


@router.get("/personas", response_model=list[schemas.PersonaResumen])
def listar_personas(
    q: str | None = None,
    dni: str | None = None,
    telefono: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> list[schemas.PersonaResumen]:
    try:
        return service.buscar_personas(
            db, texto=q, dni=dni, telefono=telefono, limite=limit, offset=offset
        )
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.post(
    "/personas",
    response_model=schemas.PersonaDetalle,
    status_code=status.HTTP_201_CREATED,
)
def crear_persona(
    datos: schemas.PersonaNueva,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(_escribir()),
) -> schemas.PersonaDetalle:
    try:
        return service.crear_persona(db, datos, creado_por=actor.id)
    except service.DniDuplicado as exc:
        raise _dni_duplicado(exc) from exc
    except service.PosibleDuplicado as exc:
        raise _posible_duplicado(exc) from exc
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.get("/personas/{persona_id}", response_model=schemas.PersonaDetalle)
def obtener_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> schemas.PersonaDetalle:
    persona = service.obtener_persona(db, persona_id)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada"
        )
    return persona


@router.patch("/personas/{persona_id}", response_model=schemas.PersonaDetalle)
def actualizar_persona(
    persona_id: int,
    datos: schemas.PersonaActualizar,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_escribir()),
) -> schemas.PersonaDetalle:
    try:
        return service.actualizar_persona(db, persona_id, datos)
    except service.PersonaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada"
        ) from exc
    except service.DniDuplicado as exc:
        raise _dni_duplicado(exc) from exc
    except service.PosibleDuplicado as exc:
        raise _posible_duplicado(exc) from exc
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.put("/personas/{persona_id}/telefonos", response_model=schemas.PersonaDetalle)
def reemplazar_telefonos(
    persona_id: int,
    datos: schemas.TelefonosUpdate,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_escribir()),
) -> schemas.PersonaDetalle:
    try:
        return service.reemplazar_telefonos(db, persona_id, datos)
    except service.PersonaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada"
        ) from exc
    except service.PosibleDuplicado as exc:
        raise _posible_duplicado(exc) from exc
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.post(
    "/pacientes",
    response_model=schemas.PacienteDetalle,
    status_code=status.HTTP_201_CREATED,
)
def crear_paciente(
    datos: schemas.PacienteNuevo,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_escribir()),
) -> schemas.PacienteDetalle:
    try:
        return service.crear_paciente(db, datos)
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.get("/pacientes", response_model=list[schemas.PacienteResumen])
def listar_pacientes(
    q: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> list[schemas.PacienteResumen]:
    return service.buscar_pacientes(db, texto=q, limite=limit, offset=offset)


@router.get("/pacientes/{paciente_id}", response_model=schemas.PacienteDetalle)
def obtener_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> schemas.PacienteDetalle:
    paciente = service.obtener_paciente(db, paciente_id)
    if paciente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado"
        )
    return paciente


@router.patch("/pacientes/{paciente_id}", response_model=schemas.PacienteDetalle)
def actualizar_paciente(
    paciente_id: int,
    datos: schemas.PacienteActualizar,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_escribir()),
) -> schemas.PacienteDetalle:
    try:
        return service.actualizar_paciente(db, paciente_id, datos)
    except service.PacienteNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado"
        ) from exc
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.get(
    "/pacientes/{paciente_id}/titulares",
    response_model=list[schemas.TitularVigente],
)
def obtener_titulares(
    paciente_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> list[schemas.TitularVigente]:
    if service.obtener_paciente(db, paciente_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado"
        )
    return service.titulares_vigentes(db, paciente_id)


@router.get("/empleados", response_model=list[schemas.EmpleadoDetalle])
def listar_empleados(
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> list[schemas.EmpleadoDetalle]:
    return service.listar_empleados(db)


@router.get("/empleados/{empleado_id}", response_model=schemas.EmpleadoDetalle)
def obtener_empleado(
    empleado_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> schemas.EmpleadoDetalle:
    empleado = service.obtener_empleado(db, empleado_id)
    if empleado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado"
        )
    return empleado


@router.post(
    "/empleados",
    response_model=schemas.EmpleadoDetalle,
    status_code=status.HTTP_201_CREATED,
)
def crear_empleado(
    datos: schemas.EmpleadoNuevo,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(_escribir()),
    _duenio: UsuarioActual = Depends(_DUENIO),
) -> schemas.EmpleadoDetalle:
    try:
        return service.crear_empleado(db, datos, creado_por=actor.id)
    except service.DniDuplicado as exc:
        raise _dni_duplicado(exc) from exc
    except service.PosibleDuplicado as exc:
        raise _posible_duplicado(exc) from exc
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.patch("/empleados/{empleado_id}", response_model=schemas.EmpleadoDetalle)
def actualizar_empleado(
    empleado_id: int,
    datos: schemas.EmpleadoActualizar,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_escribir()),
    _duenio: UsuarioActual = Depends(_DUENIO),
) -> schemas.EmpleadoDetalle:
    try:
        return service.actualizar_empleado(db, empleado_id, datos)
    except service.EmpleadoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado"
        ) from exc
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.get("/especies", response_model=list[schemas.EspecieOut])
def listar_especies(
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> list[schemas.EspecieOut]:
    return service.listar_especies(db)


@router.get("/razas", response_model=list[schemas.RazaOut])
def listar_razas(
    especie_id: int | None = None,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> list[schemas.RazaOut]:
    return service.listar_razas(db, especie_id)


@router.post(
    "/razas",
    response_model=schemas.RazaOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_raza(
    datos: schemas.RazaNueva,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_escribir()),
) -> schemas.RazaOut:
    try:
        return service.crear_raza(db, datos)
    except service.DatosInvalidos as exc:
        raise _datos_invalidos(exc) from exc


@router.get("/tamanios", response_model=list[schemas.TamanioOut])
def listar_tamanios(
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer()),
) -> list[schemas.TamanioOut]:
    return service.listar_tamanios(db)
