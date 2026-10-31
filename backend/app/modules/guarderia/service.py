"""Consultas y reglas de negocio para el cupo de guardería."""

from __future__ import annotations

import calendar
from collections.abc import Callable
from datetime import date, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import transaccion_inmediata
from app.core.parametros import get_param
from app.modules.cobros import service as cobros_service
from app.modules.guarderia import cupo, repository
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import (
    EstadoReserva,
    Ocupacion,
    Reserva,
    ReservaPaciente,
)
from app.modules.guarderia.schemas import (
    Disponibilidad,
    FranjaSinLugar,
    OcupacionExistente,
    ReservaCrear,
    ReservaOut,
    ReservaPacienteOut,
    ReservaSenaCrear,
    ResultadoCupo,
)
from app.modules.guarderia.tramos import TramoInvalido, franjas_del_tramo
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import PacienteDetalle


class DatosInvalidos(ValueError):
    """Los datos no permiten verificar un pedido de cupo."""


class PacienteNoEncontrado(ValueError):
    """Uno de los pacientes solicitados no existe."""


class RangoCalendarioInvalido(ValueError):
    """El rango del calendario es inválido o excede el límite técnico."""


class ReservaInvalida(ValueError):
    """Los datos no cumplen las reglas para crear o actualizar una reserva."""


class ReservaNoEncontrada(ValueError):
    """La reserva solicitada no existe."""


class IdempotenciaReservaConflicto(ValueError):
    """Una clave de idempotencia ya se usó con otro cuerpo."""


class ReservaCupoConflicto(ValueError):
    def __init__(self, resultado: ResultadoCupo) -> None:
        super().__init__(resultado.codigo)
        self.resultado = resultado


class EstadoReservaInvalido(ValueError):
    """La reserva no admite el cambio solicitado."""


def _configuracion_cupo(db: Session) -> tuple[int, int]:
    cupo_maximo = get_param(db, "guarderia.cupo_maximo")
    plazas_emergencia = get_param(db, "guarderia.plazas_emergencia")
    if type(cupo_maximo) is not int or type(plazas_emergencia) is not int:
        raise ValueError("La configuración de cupo debe contener valores enteros")
    return cupo_maximo, plazas_emergencia


def _obtener_pacientes(
    db: Session,
    paciente_ids: list[int],
) -> dict[int, PacienteDetalle]:
    pacientes = padron_service.obtener_pacientes(db, paciente_ids)
    faltantes = sorted(set(paciente_ids) - pacientes.keys())
    if faltantes:
        raise PacienteNoEncontrado(f"El paciente {faltantes[0]} no existe")
    return pacientes


def _completar_pacientes_de_ocupaciones(
    db: Session,
    ocupaciones: list[Ocupacion],
    pacientes: dict[int, PacienteDetalle] | None = None,
) -> dict[int, PacienteDetalle]:
    resultado = dict(pacientes or {})
    ids = {ocupacion.paciente_id for ocupacion in ocupaciones} - resultado.keys()
    resultado.update(_obtener_pacientes(db, list(ids)))
    return resultado


def _cantidad_ocupada(
    ocupaciones: list[Ocupacion],
    pacientes: dict[int, PacienteDetalle],
) -> int:
    return sum(
        cupo.plazas_por_animal(pacientes[ocupacion.paciente_id])
        for ocupacion in ocupaciones
    )


def _armar_disponibilidad(
    fecha: date,
    franja: Franja,
    cupo_maximo: int,
    plazas_emergencia: int,
    habilitaciones: int,
    ocupado: int,
) -> Disponibilidad:
    habilitadas = min(habilitaciones, plazas_emergencia)
    publico = cupo_maximo - plazas_emergencia + habilitadas
    return Disponibilidad(
        fecha=fecha,
        franja=franja,
        cupo_maximo=cupo_maximo,
        plazas_emergencia=plazas_emergencia,
        habilitadas=habilitadas,
        publico=publico,
        ocupado=ocupado,
        disponible=publico - ocupado,
    )


def calcular_disponibilidad(
    db: Session,
    fecha: date,
    franja: Franja,
) -> Disponibilidad:
    cupo_maximo, plazas_emergencia = _configuracion_cupo(db)
    ocupaciones = repository.listar_ocupaciones(db, fecha, fecha)
    ocupaciones = [
        ocupacion for ocupacion in ocupaciones if ocupacion.franja == franja
    ]
    pacientes = _completar_pacientes_de_ocupaciones(db, ocupaciones)
    ocupado = _cantidad_ocupada(ocupaciones, pacientes)
    habilitaciones = repository.contar_habilitaciones(db, fecha, franja)
    return _armar_disponibilidad(
        fecha,
        franja,
        cupo_maximo,
        plazas_emergencia,
        habilitaciones,
        ocupado,
    )


def disponibilidad(db: Session, fecha: date, franja: Franja) -> Disponibilidad:
    return calcular_disponibilidad(db, fecha, franja)


def calendario(db: Session, desde: date, hasta: date) -> list[Disponibilidad]:
    if desde > hasta:
        raise RangoCalendarioInvalido("La fecha hasta debe ser igual o posterior a desde")
    dias = (hasta - desde).days + 1
    if dias > get_settings().guarderia_calendario_max_dias:
        raise RangoCalendarioInvalido(
            "El rango del calendario supera el máximo técnico configurado"
        )

    cupo_maximo, plazas_emergencia = _configuracion_cupo(db)
    ocupaciones = repository.listar_ocupaciones(db, desde, hasta)
    pacientes = _completar_pacientes_de_ocupaciones(db, ocupaciones)
    ocupacion_por_franja: dict[tuple[date, Franja], int] = {}
    for ocupacion in ocupaciones:
        clave = (ocupacion.fecha, ocupacion.franja)
        ocupacion_por_franja[clave] = (
            ocupacion_por_franja.get(clave, 0)
            + cupo.plazas_por_animal(pacientes[ocupacion.paciente_id])
        )
    habilitaciones = repository.contar_habilitaciones_por_franja(db, desde, hasta)

    filas: list[Disponibilidad] = []
    fecha = desde
    while fecha <= hasta:
        for franja in Franja:
            clave = (fecha, franja)
            filas.append(
                _armar_disponibilidad(
                    fecha,
                    franja,
                    cupo_maximo,
                    plazas_emergencia,
                    habilitaciones.get(clave, 0),
                    ocupacion_por_franja.get(clave, 0),
                )
            )
        fecha += timedelta(days=1)
    return filas


def verificar_cupo(
    db: Session,
    paciente_ids: list[int],
    desde: tuple[date, Franja],
    hasta: tuple[date, Franja],
) -> ResultadoCupo:
    if not paciente_ids:
        raise DatosInvalidos("El pedido debe incluir al menos un paciente")
    if len(set(paciente_ids)) != len(paciente_ids):
        raise DatosInvalidos("El pedido no puede repetir pacientes")

    tramos = franjas_del_tramo(desde[0], desde[1], hasta[0], hasta[1])
    ocupaciones = repository.listar_ocupaciones(
        db, desde[0], hasta[0]
    )
    ids_pacientes = set(paciente_ids) | {
        ocupacion.paciente_id for ocupacion in ocupaciones
    }
    pacientes_ocupados = _obtener_pacientes(db, list(ids_pacientes))
    pacientes_pedido = {
        paciente_id: pacientes_ocupados[paciente_id] for paciente_id in paciente_ids
    }
    ocupacion_por_franja: dict[tuple[date, Franja], int] = {}
    for ocupacion in ocupaciones:
        clave = (ocupacion.fecha, ocupacion.franja)
        ocupacion_por_franja[clave] = (
            ocupacion_por_franja.get(clave, 0)
            + cupo.plazas_por_animal(pacientes_ocupados[ocupacion.paciente_id])
        )

    cupo_maximo, plazas_emergencia = _configuracion_cupo(db)
    habilitaciones = repository.contar_habilitaciones_por_franja(
        db, desde[0], hasta[0]
    )
    necesita = sum(
        cupo.plazas_por_animal(paciente) for paciente in pacientes_pedido.values()
    )
    tramos_set = set(tramos)
    ocupaciones_existentes = [
        OcupacionExistente(
            paciente_id=ocupacion.paciente_id,
            fecha=ocupacion.fecha,
            franja=ocupacion.franja,
        )
        for ocupacion in ocupaciones
        if ocupacion.paciente_id in pacientes_pedido
        and (ocupacion.fecha, ocupacion.franja) in tramos_set
    ]
    franjas_sin_lugar: list[FranjaSinLugar] = []
    for fecha, franja in tramos:
        fila = _armar_disponibilidad(
            fecha,
            franja,
            cupo_maximo,
            plazas_emergencia,
            habilitaciones.get((fecha, franja), 0),
            ocupacion_por_franja.get((fecha, franja), 0),
        )
        if fila.disponible < necesita:
            franjas_sin_lugar.append(
                FranjaSinLugar(
                    fecha=fecha,
                    franja=franja,
                    necesita=necesita,
                    disponible=fila.disponible,
                )
            )

    codigo: Literal["DISPONIBLE", "SIN_CUPO", "YA_RESERVADO"]
    if ocupaciones_existentes:
        codigo = "YA_RESERVADO"
    elif franjas_sin_lugar:
        codigo = "SIN_CUPO"
    else:
        codigo = "DISPONIBLE"
    return ResultadoCupo(
        aprobado=codigo == "DISPONIBLE",
        codigo=codigo,
        franjas_sin_lugar=franjas_sin_lugar,
        ocupaciones_existentes=ocupaciones_existentes,
    )


def _validar_datos_reserva(
    db: Session,
    solicitud: ReservaCrear,
    *,
    hoy: date,
) -> list[tuple[date, Franja]]:
    if solicitud.desde_fecha < hoy:
        raise ReservaInvalida("La fecha de inicio no puede estar en el pasado")
    max_meses = get_param(db, "guarderia.reserva_max_meses")
    if type(max_meses) is not int or max_meses < 0:
        raise ValueError("La anticipación máxima debe ser un entero no negativo")
    fecha_limite = _sumar_meses(hoy, max_meses)
    if solicitud.hasta_fecha > fecha_limite:
        raise ReservaInvalida(
            f"La fecha de fin supera la anticipación máxima de {max_meses} meses"
        )

    try:
        tramos = franjas_del_tramo(
            solicitud.desde_fecha,
            solicitud.desde_franja,
            solicitud.hasta_fecha,
            solicitud.hasta_franja,
        )
    except TramoInvalido as exc:
        raise ReservaInvalida(str(exc)) from exc

    if padron_service.obtener_persona(db, solicitud.tutor_persona_id) is None:
        raise ReservaInvalida("El tutor no existe")

    pacientes = padron_service.obtener_pacientes(db, solicitud.paciente_ids)
    if set(pacientes) != set(solicitud.paciente_ids):
        raise ReservaInvalida("Uno o más animales no existen")
    for paciente_id in solicitud.paciente_ids:
        paciente = pacientes[paciente_id]
        if not paciente.activo:
            raise ReservaInvalida(f"El animal {paciente_id} no está activo")
        titulares = padron_service.titulares_vigentes(db, paciente_id)
        if not any(
            titular.persona_id == solicitud.tutor_persona_id
            for titular in titulares
        ):
            raise ReservaInvalida(
                f"El tutor no es titular vigente del animal {paciente_id}"
            )
    return tramos


def _sumar_meses(fecha: date, meses: int) -> date:
    indice_mes = fecha.month - 1 + meses
    anio = fecha.year + indice_mes // 12
    mes = indice_mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def confirmar_reserva_por_sena(db: Session, cargo_id: int) -> None:
    """Confirma la reserva referenciada cuando Cobros registra su seña."""
    reserva = repository.obtener_reserva_por_cargo(db, cargo_id)
    if reserva is None or reserva.estado != EstadoReserva.PENDIENTE_SENA:
        return
    if cobros_service.total_senas_cargo(db, cargo_id) > 0:
        reserva.estado = EstadoReserva.CONFIRMADA
        db.flush()


def _misma_solicitud(
    db: Session,
    reserva: Reserva,
    solicitud: ReservaCrear,
) -> bool:
    if reserva.cargo_id is None:
        return False
    cuidados_existentes = {
        paciente.paciente_id: paciente.cuidados_extras
        for paciente in repository.pacientes_de_reserva(db, reserva.id)
    }
    cuidados_solicitados = {
        cuidado.paciente_id: cuidado.cuidados_extras
        for cuidado in solicitud.cuidados_extras
    }
    return (
        reserva.tutor_persona_id == solicitud.tutor_persona_id
        and reserva.desde_fecha == solicitud.desde_fecha
        and reserva.desde_franja == solicitud.desde_franja
        and reserva.hasta_fecha == solicitud.hasta_fecha
        and reserva.hasta_franja == solicitud.hasta_franja
        and cuidados_existentes == cuidados_solicitados
        and cobros_service.total_inicial_cargo(db, reserva.cargo_id)
        == solicitud.total_centavos
    )


def _reserva_out(db: Session, reserva: Reserva) -> ReservaOut:
    total_centavos = (
        cobros_service.total_vigente_cargo(db, reserva.cargo_id)
        if reserva.cargo_id is not None
        else None
    )
    return ReservaOut(
        id=reserva.id,
        tutor_persona_id=reserva.tutor_persona_id,
        desde_fecha=reserva.desde_fecha,
        desde_franja=reserva.desde_franja,
        hasta_fecha=reserva.hasta_fecha,
        hasta_franja=reserva.hasta_franja,
        estado=reserva.estado,
        cargo_id=reserva.cargo_id,
        total_centavos=total_centavos,
        pacientes=[
            ReservaPacienteOut(
                paciente_id=paciente.paciente_id,
                cuidados_extras=paciente.cuidados_extras,
            )
            for paciente in repository.pacientes_de_reserva(db, reserva.id)
        ],
        created_at=reserva.created_at,
    )


def crear_reserva(
    db: Session,
    solicitud: ReservaCrear,
    *,
    clave_idempotencia: str,
    usuario_id: int,
    reloj: Callable[[], date] | None = None,
) -> tuple[ReservaOut, bool]:
    if not clave_idempotencia.strip():
        raise ReservaInvalida("Idempotency-Key no puede estar vacía")

    reserva: Reserva
    creada = False
    with transaccion_inmediata(db):
        existente = repository.obtener_reserva_por_clave(db, clave_idempotencia)
        if existente is not None:
            if not _misma_solicitud(db, existente, solicitud):
                raise IdempotenciaReservaConflicto(
                    "Idempotency-Key ya utilizada con distinto cuerpo"
                )
            reserva = existente
        else:
            tramos = _validar_datos_reserva(
                db,
                solicitud,
                hoy=reloj() if reloj is not None else date.today(),
            )
            resultado = verificar_cupo(
                db,
                solicitud.paciente_ids,
                (solicitud.desde_fecha, solicitud.desde_franja),
                (solicitud.hasta_fecha, solicitud.hasta_franja),
            )
            if resultado.codigo != "DISPONIBLE":
                raise ReservaCupoConflicto(resultado)

            reserva = Reserva(
                tutor_persona_id=solicitud.tutor_persona_id,
                desde_fecha=solicitud.desde_fecha,
                desde_franja=solicitud.desde_franja,
                hasta_fecha=solicitud.hasta_fecha,
                hasta_franja=solicitud.hasta_franja,
                estado=EstadoReserva.PENDIENTE_SENA,
                clave_idempotencia=clave_idempotencia,
                creado_por=usuario_id,
            )
            repository.crear_reserva(db, reserva)
            repository.agregar_pacientes_reserva(
                db,
                [
                    ReservaPaciente(
                        reserva_id=reserva.id,
                        paciente_id=paciente_id,
                        cuidados_extras=next(
                            cuidado.cuidados_extras
                            for cuidado in solicitud.cuidados_extras
                            if cuidado.paciente_id == paciente_id
                        ),
                    )
                    for paciente_id in solicitud.paciente_ids
                ],
            )
            repository.agregar_ocupaciones(
                db,
                [
                    Ocupacion(
                        fecha=fecha,
                        franja=franja,
                        reserva_id=reserva.id,
                        paciente_id=paciente_id,
                    )
                    for paciente_id in solicitud.paciente_ids
                    for fecha, franja in tramos
                ],
            )
            cargo = cobros_service.crear_cargo(
                db,
                persona_id=solicitud.tutor_persona_id,
                concepto=f"Reserva de guardería #{reserva.id}",
                total_centavos=solicitud.total_centavos,
                referencia_tipo="RESERVA",
                referencia_id=reserva.id,
                usuario_id=usuario_id,
                transaccion_externa=True,
            )
            reserva.cargo_id = cargo.id
            db.flush()
            creada = True

    db.refresh(reserva)
    return _reserva_out(db, reserva), creada


def registrar_sena(
    db: Session,
    reserva_id: int,
    solicitud: ReservaSenaCrear,
    *,
    clave_idempotencia: str,
    usuario_id: int,
    empleado_id: int | None,
) -> ReservaOut:
    if not clave_idempotencia.strip():
        raise ReservaInvalida("Idempotency-Key no puede estar vacía")

    with transaccion_inmediata(db):
        reserva = repository.obtener_reserva(db, reserva_id)
        if reserva is None:
            raise ReservaNoEncontrada("Reserva no encontrada")
        if reserva.cargo_id is None:
            raise ReservaInvalida("La reserva no tiene un cargo asociado")
        if reserva.estado not in {
            EstadoReserva.PENDIENTE_SENA,
            EstadoReserva.CONFIRMADA,
        }:
            raise EstadoReservaInvalido(
                "La reserva no admite el registro de una seña"
            )

        cobros_service.registrar_pago(
            db,
            cargo_id=reserva.cargo_id,
            monto_centavos=solicitud.monto_centavos,
            medio=solicitud.medio,
            es_sena=True,
            usuario_id=usuario_id,
            empleado_id=empleado_id,
            clave_idempotencia=clave_idempotencia,
            transaccion_externa=True,
        )
        reserva.estado = EstadoReserva.CONFIRMADA
        db.flush()

    db.refresh(reserva)
    return _reserva_out(db, reserva)


def obtener_reserva(db: Session, reserva_id: int) -> ReservaOut:
    reserva = repository.obtener_reserva(db, reserva_id)
    if reserva is None:
        raise ReservaNoEncontrada("Reserva no encontrada")
    return _reserva_out(db, reserva)


def listar_reservas(
    db: Session,
    *,
    desde: date | None,
    hasta: date | None,
    estado: EstadoReserva | None,
    persona_id: int | None,
) -> list[ReservaOut]:
    if desde is not None and hasta is not None and desde > hasta:
        raise RangoCalendarioInvalido("La fecha hasta debe ser igual o posterior a desde")
    return [
        _reserva_out(db, reserva)
        for reserva in repository.listar_reservas(
            db,
            desde=desde,
            hasta=hasta,
            estado=estado,
            persona_id=persona_id,
        )
    ]
