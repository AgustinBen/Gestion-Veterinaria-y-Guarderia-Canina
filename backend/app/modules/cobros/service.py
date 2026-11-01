"""Servicio público del módulo cobros.

Las firmas requeridas por el ticket se mantienen tal como se pide.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.modules.cobros import models, repository, schemas
from app.modules.cobros.dinero import DineroError, formatear_pesos, validar_positivo
from app.modules.identidad.permisos import Rol
from app.modules.padron import service as padron_service

logger = logging.getLogger(__name__)


class CobrosError(Exception):
    pass


class CargoNoEncontrado(CobrosError):
    pass


class PersonaNoEncontrada(CobrosError):
    pass


class PacienteNoEncontrado(CobrosError):
    pass


class PagoNoEncontrado(CobrosError):
    pass


class SaldoInsuficiente(CobrosError):
    def __init__(self, saldo_restante: int) -> None:
        super().__init__(f"Saldo insuficiente. Saldo restante: {saldo_restante}")
        self.saldo_restante = saldo_restante


class CargoYaSaldado(CobrosError):
    def __init__(self, saldo_restante: int) -> None:
        super().__init__(f"El cargo ya se encuentra saldado. Saldo restante: {saldo_restante}")
        self.saldo_restante = saldo_restante


class CargoPagadoCompleto(CobrosError):
    def __init__(self) -> None:
        super().__init__("El cargo ya está pagado por completo")


class TotalMenorAPagado(CobrosError):
    def __init__(self, total_pagado: int) -> None:
        super().__init__(
            "El nuevo total no puede ser menor a lo ya pagado "
            f"({formatear_pesos(total_pagado)})"
        )
        self.total_pagado = total_pagado


class MotivoRequerido(CobrosError):
    def __init__(self) -> None:
        super().__init__("Falta el motivo del ajuste")


class TotalSinCambios(CobrosError):
    def __init__(self) -> None:
        super().__init__("El nuevo total es igual al total vigente")


class AjusteNoPermitido(CobrosError):
    def __init__(self) -> None:
        super().__init__("Solo el Dueño puede bajar el precio del cargo")


class MedioPagoInvalido(CobrosError):
    pass


class CargoReservaRequiereSena(CobrosError):
    pass


class IdempotenciaConflicto(CobrosError):
    pass


class ReversoNoPermitido(CobrosError):
    pass


class AccesoDenegado(CobrosError):
    pass


class TransaccionNoDisponible(CobrosError):
    def __init__(self) -> None:
        super().__init__(
            "No se pudo iniciar una transacción segura. Intente nuevamente."
        )


class OrdenDeudoresInvalida(CobrosError):
    pass


def _validar_monto_positivo(monto_centavos: int) -> int:
    try:
        return validar_positivo(monto_centavos)
    except DineroError as exc:
        raise CobrosError(str(exc)) from exc


def _obtener_cargo_o_error(db: Session, cargo_id: int) -> models.Cargo:
    cargo = repository.obtener_cargo(db, cargo_id)
    if cargo is None:
        raise CargoNoEncontrado("Cargo no encontrado")
    return cargo


def total_inicial_cargo(db: Session, cargo_id: int) -> int:
    """Devuelve el total original del cargo a otros módulos, sin exponer su modelo."""
    return int(_obtener_cargo_o_error(db, cargo_id).total_inicial)


def total_vigente_cargo(db: Session, cargo_id: int) -> int:
    """Devuelve el total actual del cargo, incluidos sus ajustes."""
    _obtener_cargo_o_error(db, cargo_id)
    return int(repository.total_vigente(db, cargo_id))


def total_senas_cargo(db: Session, cargo_id: int) -> int:
    """Devuelve el importe neto de señas registradas para un cargo."""
    _obtener_cargo_o_error(db, cargo_id)
    return repository.total_senas(db, cargo_id)


def cerrar_cargo_por_cancelacion(
    db: Session,
    *,
    cargo_id: int,
    usuario_id: int,
    transaccion_externa: bool = False,
) -> models.AjustePrecio | None:
    """Cierra el saldo de una reserva cancelada sin borrar ni revertir pagos."""
    if not transaccion_externa:
        _iniciar_transaccion(db)

    try:
        cargo = _obtener_cargo_o_error(db, cargo_id)
        if cargo.referencia_tipo != "RESERVA":
            raise CobrosError("Solo se pueden cerrar cargos de reservas canceladas")

        total_vigente = repository.total_vigente(db, cargo_id)
        total_pagado = repository.total_pagado(db, cargo_id)
        if total_pagado > total_vigente:
            raise TotalMenorAPagado(total_pagado)
        if total_pagado == total_vigente:
            if not transaccion_externa:
                db.commit()
            return None

        ajuste = repository.crear_ajuste(
            db,
            cargo_id=cargo_id,
            precio_anterior=total_vigente,
            precio_nuevo=total_pagado,
            motivo="Cierre del saldo por cancelación de reserva",
            usuario_id=usuario_id,
        )
        if not transaccion_externa:
            db.commit()
            db.refresh(ajuste)
        return ajuste
    except Exception:
        if not transaccion_externa:
            db.rollback()
        raise


def _iniciar_transaccion(db: Session) -> None:
    """Serializa escrituras con BEGIN IMMEDIATE (SQLite).

    Solo la contención de bloqueo de SQLite se transforma en un error
    recuperable; los demás errores de base de datos se propagan.
    """
    try:
        db.execute(text("BEGIN IMMEDIATE"))
    except OperationalError as exc:
        codigo_sqlite = getattr(exc.orig, "sqlite_errorcode", None)
        if not isinstance(codigo_sqlite, int) or codigo_sqlite & 0xFF not in {
            sqlite3.SQLITE_BUSY,
            sqlite3.SQLITE_LOCKED,
        }:
            db.rollback()
            raise

        logger.warning(
            "SQLite no pudo adquirir el bloqueo para BEGIN IMMEDIATE "
            "(código %s)",
            codigo_sqlite,
            exc_info=True,
        )
        db.rollback()
        raise TransaccionNoDisponible() from exc


def _pago_idempotente(
    db: Session,
    *,
    clave: str,
    cargo_id: int,
    monto: int,
    medio: str,
    es_sena: bool,
) -> models.Pago | None:
    """Devuelve el pago ya creado para la clave, o 409 si el cuerpo difiere."""
    existente = repository.obtener_pago_por_clave_idempotencia(db, clave)
    if existente is None:
        return None
    medio_pago = repository.obtener_medio_pago(db, existente.medio_pago_id)
    medio_codigo = medio_pago.codigo if medio_pago else None
    mismo_cuerpo = (
        existente.cargo_id == cargo_id
        and existente.monto == monto
        and medio_codigo == medio.upper()
        and existente.es_sena == bool(es_sena)
    )
    if not mismo_cuerpo:
        raise IdempotenciaConflicto("Idempotency-Key ya utilizada con distinto cuerpo")
    return existente


def crear_cargo(
    db: Session,
    *,
    persona_id: int,
    concepto: str,
    total_centavos: int,
    paciente_id: int | None = None,
    referencia_tipo: str | None = None,
    referencia_id: int | None = None,
    usuario_id: int,
    transaccion_externa: bool = False,
) -> models.Cargo:
    _validar_monto_positivo(total_centavos)

    # Validar que la persona exista vía padron.service (sin importar models/repository ajenos)
    persona = padron_service.obtener_persona(db, persona_id)
    if persona is None:
        raise CobrosError("Persona no encontrada")

    if paciente_id is not None:
        paciente = padron_service.obtener_paciente(db, paciente_id)
        if paciente is None:
            raise CobrosError("Paciente no encontrado")

    cargo = models.Cargo(
        persona_id=persona_id,
        paciente_id=paciente_id,
        concepto=concepto,
        total_inicial=int(total_centavos),
        origen=models.OrigenCargo.NORMAL,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        creado_por=usuario_id,
    )
    db.add(cargo)
    if transaccion_externa:
        db.flush()
    else:
        db.commit()
    db.refresh(cargo)
    return cargo


def saldo_cargo(db: Session, cargo_id: int) -> int:
    _obtener_cargo_o_error(db, cargo_id)
    return int(repository.saldo(db, cargo_id))


def saldo_pendiente(db: Session, persona_id: int) -> int:
    # Una sola fórmula de saldo: delega en resumen_deuda (T-21).
    return resumen_deuda(db, persona_id).saldo_total_centavos


def resumen_deuda(db: Session, persona_id: int) -> schemas.ResumenDeuda:
    persona = padron_service.obtener_persona(db, persona_id)
    if persona is None:
        raise PersonaNoEncontrada("Persona no encontrada")
    fila = repository.resumen_deuda(db, persona_id)
    saldo_total = int(fila.saldo_total_centavos or 0)
    cargos = int(fila.cargos_pendientes or 0)
    fecha = fila.deuda_mas_antigua
    if fecha is not None and hasattr(fecha, "date"):
        fecha = fecha.date()
    return schemas.ResumenDeuda(
        debe=saldo_total > 0,
        saldo_total_centavos=saldo_total,
        cargos_pendientes=cargos,
        deuda_mas_antigua=fecha,
        incluye_migracion=int(fila.saldo_migracion_centavos or 0) > 0,
    )


def listar_deudores(
    db: Session,
    *,
    orden: str,
    solo_migracion: bool,
    limite: int,
    desplazamiento: int,
) -> list[schemas.DeudorOut]:
    if orden not in {"monto", "antiguedad"}:
        raise OrdenDeudoresInvalida("Orden inválido")
    filas = repository.listar_deudores(
        db,
        orden=orden,
        solo_migracion=solo_migracion,
        limite=limite,
        desplazamiento=desplazamiento,
    )
    ids = [int(fila.persona_id) for fila in filas]
    personas = padron_service.obtener_personas_resumen(db, ids)
    resultado: list[schemas.DeudorOut] = []
    for fila in filas:
        persona = personas.get(int(fila.persona_id))
        if persona is None:
            continue
        telefonos = persona.telefonos
        resultado.append(
            schemas.DeudorOut(
                persona=schemas.PersonaDeudorOut(
                    id=persona.id,
                    nombre=persona.nombre,
                    apellido=persona.apellido,
                    # El teléfono principal es el primer teléfono por id.
                    telefono_principal=telefonos[0] if telefonos else None,
                ),
                saldo_total_centavos=int(fila.saldo_total_centavos),
                cantidad_cargos_pendientes=int(fila.cantidad_cargos_pendientes),
                deuda_mas_antigua=(
                    fila.deuda_mas_antigua.date()
                    if hasattr(fila.deuda_mas_antigua, "date")
                    else fila.deuda_mas_antigua
                ),
                saldo_migracion_centavos=int(fila.saldo_migracion_centavos or 0),
            )
        )
    return resultado


def obtener_cargo_detalle(db: Session, cargo_id: int) -> schemas.CargoDetalleOut:
    cargo = _obtener_cargo_o_error(db, cargo_id)
    total_vig = repository.total_vigente(db, cargo_id)
    total_pag = repository.total_pagado(db, cargo_id)
    return schemas.CargoDetalleOut(
        id=cargo.id,
        persona_id=cargo.persona_id,
        paciente_id=cargo.paciente_id,
        concepto=cargo.concepto,
        total_inicial=cargo.total_inicial,
        origen=cargo.origen.value,
        referencia_tipo=cargo.referencia_tipo,
        referencia_id=cargo.referencia_id,
        creado_por=cargo.creado_por,
        created_at=cargo.created_at,
        total_vigente=total_vig,
        total_pagado=total_pag,
        saldo=total_vig - total_pag,
    )


ROLES_QUE_PUEDEN_BAJAR: frozenset[Rol] = frozenset({Rol.DUENIO})


def ajustar_precio(
    db: Session,
    *,
    cargo_id: int,
    nuevo_total_centavos: int,
    motivo: str,
    usuario_id: int,
    rol: Rol,
) -> models.AjustePrecio:
    """Ajusta el precio vigente de un cargo con auditoría.

    Reglas (RN-22): solo mientras haya saldo, nunca por debajo de lo ya pagado,
    con motivo obligatorio y el total nuevo distinto del vigente. Bajar el precio
    solo lo permite el Dueño.
    """
    nuevo_total = _validar_monto_positivo(nuevo_total_centavos)
    motivo_limpio = motivo.strip()
    if not motivo_limpio:
        raise MotivoRequerido()

    # Concurrencia: serializar escrituras con BEGIN IMMEDIATE (SQLite)
    _iniciar_transaccion(db)

    try:
        _obtener_cargo_o_error(db, cargo_id)
        total_vigente = repository.total_vigente(db, cargo_id)
        total_pagado = repository.total_pagado(db, cargo_id)

        if total_vigente - total_pagado <= 0:
            raise CargoPagadoCompleto()
        if nuevo_total == total_vigente:
            raise TotalSinCambios()
        if nuevo_total < total_vigente and rol not in ROLES_QUE_PUEDEN_BAJAR:
            raise AjusteNoPermitido()
        if nuevo_total < total_pagado:
            raise TotalMenorAPagado(total_pagado)

        ajuste = repository.crear_ajuste(
            db,
            cargo_id=cargo_id,
            precio_anterior=total_vigente,
            precio_nuevo=nuevo_total,
            motivo=motivo_limpio,
            usuario_id=usuario_id,
        )
        db.commit()
        db.refresh(ajuste)
        return ajuste
    except (CobrosError, IntegrityError):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def listar_ajustes(db: Session, cargo_id: int) -> list[models.AjustePrecio]:
    _obtener_cargo_o_error(db, cargo_id)
    return repository.ajustes_de_cargo(db, cargo_id)


def listar_medios_pago(db: Session) -> list[models.MedioPago]:
    return repository.listar_medios_pago_activos(db)


def registrar_pago(
    db: Session,
    *,
    cargo_id: int,
    monto_centavos: int,
    medio: str,
    es_sena: bool = False,
    usuario_id: int,
    empleado_id: int | None = None,
    fecha_pago: date | None = None,
    clave_idempotencia: str | None = None,
    transaccion_externa: bool = False,
) -> models.Pago:
    monto = _validar_monto_positivo(monto_centavos)
    if clave_idempotencia:
        existente = _pago_idempotente(
            db,
            clave=clave_idempotencia,
            cargo_id=cargo_id,
            monto=monto,
            medio=medio,
            es_sena=es_sena,
        )
        if existente is not None:
            return existente

    # Concurrencia: serializar escrituras con BEGIN IMMEDIATE (SQLite).
    # Con transacción externa el lock ya lo tomó el módulo que llama.
    if not transaccion_externa:
        _iniciar_transaccion(db)

    try:
        # Otra sesión pudo crear la misma clave mientras esperábamos el lock.
        if clave_idempotencia:
            existente = _pago_idempotente(
                db,
                clave=clave_idempotencia,
                cargo_id=cargo_id,
                monto=monto,
                medio=medio,
                es_sena=es_sena,
            )
            if existente is not None:
                # Cerrar la transacción de lectura antes de devolver.
                if not transaccion_externa:
                    db.rollback()
                return existente

        cargo = _obtener_cargo_o_error(db, cargo_id)
        if (
            cargo.referencia_tipo == "RESERVA"
            and not es_sena
            and repository.total_senas(db, cargo_id) <= 0
        ):
            raise CargoReservaRequiereSena(
                "La reserva requiere registrar una seña antes de otros pagos"
            )
        medio_pago = repository.obtener_medio_pago_por_codigo(db, medio)
        if medio_pago is None or not medio_pago.activo:
            raise MedioPagoInvalido("Medio de pago inválido")

        saldo_actual = repository.saldo(db, cargo_id)
        if saldo_actual <= 0:
            raise CargoYaSaldado(saldo_actual)
        if monto > saldo_actual:
            raise SaldoInsuficiente(saldo_actual)

        pago = models.Pago(
            cargo_id=cargo.id,
            monto=monto,
            tipo=models.TipoPago.PAGO,
            pago_revertido_id=None,
            medio_pago_id=medio_pago.id,
            es_sena=bool(es_sena),
            fecha=fecha_pago or date.today(),
            usuario_id=usuario_id,
            empleado_id=empleado_id,
            clave_idempotencia=clave_idempotencia,
        )
        db.add(pago)
        try:
            db.flush()
            if es_sena and cargo.referencia_tipo == "RESERVA":
                from app.modules.guarderia import service as guarderia_service

                guarderia_service.confirmar_reserva_por_sena(db, cargo_id)
            if not transaccion_externa:
                db.commit()
        except IntegrityError:
            # Carrera real: dos pedidos con la misma clave pasaron el chequeo.
            if transaccion_externa or not clave_idempotencia:
                raise
            db.rollback()
            existente = _pago_idempotente(
                db,
                clave=clave_idempotencia,
                cargo_id=cargo_id,
                monto=monto,
                medio=medio,
                es_sena=es_sena,
            )
            if existente is None:
                raise
            return existente
        db.refresh(pago)
        return pago
    except (CobrosError, IntegrityError):
        if not transaccion_externa:
            db.rollback()
        raise
    except Exception:
        if not transaccion_externa:
            db.rollback()
        raise


def revertir_pago(
    db: Session,
    *,
    pago_id: int,
    usuario_id: int,
    empleado_id: int | None = None,
    motivo: str | None = None,
) -> models.Pago:
    motivo_limpio = (motivo or "").strip()
    if not motivo_limpio:
        raise CobrosError("Falta el motivo del reverso")

    # Revertir crea un reverso, no borra. Solo DUENIO se controla en router.
    _iniciar_transaccion(db)

    try:
        pago_original = repository.obtener_pago(db, pago_id)
        if pago_original is None:
            raise PagoNoEncontrado("Pago no encontrado")
        if pago_original.tipo != models.TipoPago.PAGO:
            raise ReversoNoPermitido("Solo se puede revertir un pago")
        if repository.tiene_reverso(db, pago_original.id):
            raise ReversoNoPermitido("El pago ya fue revertido")

        reverso = models.Pago(
            cargo_id=pago_original.cargo_id,
            monto=pago_original.monto,
            tipo=models.TipoPago.REVERSO,
            pago_revertido_id=pago_original.id,
            medio_pago_id=pago_original.medio_pago_id,
            es_sena=False,
            fecha=date.today(),
            usuario_id=usuario_id,
            empleado_id=empleado_id,
            clave_idempotencia=None,
            motivo=motivo_limpio,
        )
        db.add(reverso)
        db.commit()
        db.refresh(reverso)
        return reverso
    except (CobrosError, IntegrityError):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def cuenta_persona(db: Session, persona_id: int) -> schemas.CuentaClienteOut:
    if padron_service.obtener_persona(db, persona_id) is None:
        raise PersonaNoEncontrada("Persona no encontrada")
    cargos = repository.cargos_de_persona(db, persona_id)
    items: list[schemas.CargoCuentaOut] = []
    saldo_total = 0
    for cargo in cargos:
        detalle = obtener_cargo_detalle(db, cargo.id)
        items.append(
            schemas.CargoCuentaOut(
                cargo=detalle,
                pagos=[
                    schemas.PagoOut.model_validate(pago)
                    for pago in repository.pagos_de_cargo(db, cargo.id)
                ],
            )
        )
        if detalle.saldo > 0:
            saldo_total += detalle.saldo
    return schemas.CuentaClienteOut(
        persona_id=persona_id, saldo_total=saldo_total, cargos=items
    )


def cuenta_paciente(db: Session, paciente_id: int) -> schemas.CuentaPacienteOut:
    if padron_service.obtener_paciente(db, paciente_id) is None:
        raise PacienteNoEncontrado("Paciente no encontrado")
    cargos = repository.cargos_de_paciente(db, paciente_id)
    items: list[schemas.CargoCuentaOut] = []
    saldo_total = 0
    for cargo in cargos:
        detalle = obtener_cargo_detalle(db, cargo.id)
        items.append(
            schemas.CargoCuentaOut(
                cargo=detalle,
                pagos=[
                    schemas.PagoOut.model_validate(pago)
                    for pago in repository.pagos_de_cargo(db, cargo.id)
                ],
            )
        )
        if detalle.saldo > 0:
            saldo_total += detalle.saldo
    return schemas.CuentaPacienteOut(
        paciente_id=paciente_id, saldo_total=saldo_total, cargos=items
    )
