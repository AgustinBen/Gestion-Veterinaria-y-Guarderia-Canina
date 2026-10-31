"""Endpoints del módulo cobros."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.cobros import schemas, service
from app.modules.identidad.deps import require_acceso, require_role
from app.modules.identidad.permisos import Nivel, Recurso, Rol
from app.modules.identidad.schemas import UsuarioActual

router = APIRouter(prefix="/api", tags=["cobros"])

_DUENIO = require_role(Rol.DUENIO)


def _escribir_deudas_cobros() -> Callable[..., UsuarioActual]:
    return require_acceso(Recurso.DEUDAS_COBROS, Nivel.ESCRITURA)


def _leer_deudas_cobros() -> Callable[..., UsuarioActual]:
    return require_acceso(Recurso.DEUDAS_COBROS, Nivel.LECTURA)


def _leer_finanzas() -> Callable[..., UsuarioActual]:
    return require_acceso(Recurso.FINANZAS, Nivel.LECTURA)


@router.get("/medios-pago", response_model=list[schemas.MedioPagoOut])
def listar_medios_pago(
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_deudas_cobros()),
) -> list[schemas.MedioPagoOut]:
    medios = service.listar_medios_pago(db)
    return [schemas.MedioPagoOut.model_validate(m) for m in medios]


@router.get("/deudores", response_model=list[schemas.DeudorOut])
def listar_deudores(
    orden: Literal["monto", "antiguedad"] = Query(default="monto"),
    solo_migracion: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    # El listado global de deudores es información financiera: solo el Dueño.
    # Personal sigue viendo la deuda del cliente dentro de su cuenta.
    _usuario: UsuarioActual = Depends(_leer_finanzas()),
) -> list[schemas.DeudorOut]:
    try:
        return service.listar_deudores(
            db,
            orden=orden,
            solo_migracion=solo_migracion,
            limite=limit,
            desplazamiento=offset,
        )
    except service.OrdenDeudoresInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get("/personas/{persona_id}/deuda", response_model=schemas.ResumenDeuda)
def resumen_deuda(
    persona_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_deudas_cobros()),
) -> schemas.ResumenDeuda:
    try:
        return service.resumen_deuda(db, persona_id)
    except service.PersonaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except service.CobrosError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.post("/cargos", response_model=schemas.CargoOut, status_code=status.HTTP_201_CREATED)
def crear_cargo(
    datos: schemas.CargoCrear,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(_escribir_deudas_cobros()),
) -> schemas.CargoOut:
    try:
        cargo = service.crear_cargo(
            db,
            persona_id=datos.persona_id,
            concepto=datos.concepto,
            total_centavos=datos.total_centavos,
            paciente_id=datos.paciente_id,
            referencia_tipo=datos.referencia_tipo,
            referencia_id=datos.referencia_id,
            usuario_id=usuario.id,
        )
    except service.CobrosError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return schemas.CargoOut.model_validate(cargo)


@router.get("/cargos/{cargo_id}", response_model=schemas.CargoDetalleOut)
def obtener_cargo(
    cargo_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_deudas_cobros()),
) -> schemas.CargoDetalleOut:
    try:
        return service.obtener_cargo_detalle(db, cargo_id)
    except service.CargoNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cargo no encontrado") from exc


@router.post("/cargos/{cargo_id}/ajustes", response_model=schemas.AjustePrecioOut)
def ajustar_precio(
    cargo_id: int,
    datos: schemas.AjustePrecioCrear,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(_escribir_deudas_cobros()),
) -> schemas.AjustePrecioOut:
    try:
        ajuste = service.ajustar_precio(
            db,
            cargo_id=cargo_id,
            nuevo_total_centavos=datos.nuevo_total_centavos,
            motivo=datos.motivo,
            usuario_id=usuario.id,
            rol=usuario.rol,
        )
    except service.CargoNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cargo no encontrado") from exc
    except service.AjusteNoPermitido as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except service.TransaccionNoDisponible as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except service.CobrosError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return schemas.AjustePrecioOut.model_validate(ajuste)


@router.get("/cargos/{cargo_id}/ajustes", response_model=list[schemas.AjustePrecioOut])
def listar_ajustes(
    cargo_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_deudas_cobros()),
) -> list[schemas.AjustePrecioOut]:
    try:
        ajustes = service.listar_ajustes(db, cargo_id)
    except service.CargoNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cargo no encontrado") from exc
    except service.CobrosError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return [schemas.AjustePrecioOut.model_validate(ajuste) for ajuste in ajustes]


@router.post("/cargos/{cargo_id}/pagos", response_model=schemas.PagoOut)
def registrar_pago(
    cargo_id: int,
    datos: schemas.PagoCrear,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(_escribir_deudas_cobros()),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> schemas.PagoOut:
    try:
        pago = service.registrar_pago(
            db,
            cargo_id=cargo_id,
            monto_centavos=datos.monto_centavos,
            medio=datos.medio,
            es_sena=datos.es_sena,
            usuario_id=usuario.id,
            empleado_id=usuario.empleado_id,
            fecha_pago=datos.fecha,
            clave_idempotencia=idempotency_key,
        )
    except service.CargoNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cargo no encontrado") from exc
    except service.MedioPagoInvalido as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except service.SaldoInsuficiente as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except service.CargoYaSaldado as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except service.IdempotenciaConflicto as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except service.TransaccionNoDisponible as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except service.CobrosError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return schemas.PagoOut.model_validate(pago)


@router.post("/pagos/{pago_id}/revertir", response_model=schemas.PagoOut)
def revertir_pago(
    pago_id: int,
    datos: schemas.PagoRevertir,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(_DUENIO),
) -> schemas.PagoOut:
    try:
        reverso = service.revertir_pago(
            db,
            pago_id=pago_id,
            usuario_id=usuario.id,
            empleado_id=usuario.empleado_id,
            motivo=datos.motivo,
        )
    except service.PagoNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado") from exc
    except service.ReversoNoPermitido as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except service.TransaccionNoDisponible as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except service.CobrosError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return schemas.PagoOut.model_validate(reverso)


@router.get("/personas/{persona_id}/cuenta", response_model=schemas.CuentaClienteOut)
def cuenta_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_deudas_cobros()),
) -> schemas.CuentaClienteOut:
    try:
        return service.cuenta_persona(db, persona_id)
    except service.PersonaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except service.CobrosError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("/pacientes/{paciente_id}/cuenta", response_model=schemas.CuentaPacienteOut)
def cuenta_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_leer_deudas_cobros()),
) -> schemas.CuentaPacienteOut:
    try:
        return service.cuenta_paciente(db, paciente_id)
    except service.PacienteNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except service.CobrosError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
