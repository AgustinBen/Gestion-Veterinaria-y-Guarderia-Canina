"""Consultas y reglas de negocio para el cupo de guardería."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.parametros import get_param
from app.modules.guarderia import cupo, repository
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import Ocupacion
from app.modules.guarderia.schemas import (
    Disponibilidad,
    FranjaSinLugar,
    OcupacionExistente,
    ResultadoCupo,
)
from app.modules.guarderia.tramos import franjas_del_tramo
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import PacienteDetalle


class DatosInvalidos(ValueError):
    """Los datos no permiten verificar un pedido de cupo."""


class PacienteNoEncontrado(ValueError):
    """Uno de los pacientes solicitados no existe."""


class RangoCalendarioInvalido(ValueError):
    """El rango del calendario es inválido o excede el límite técnico."""


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
    pacientes: dict[int, PacienteDetalle] = {}
    for paciente_id in set(paciente_ids):
        paciente = padron_service.obtener_paciente(db, paciente_id)
        if paciente is None:
            raise PacienteNoEncontrado(f"El paciente {paciente_id} no existe")
        pacientes[paciente_id] = paciente
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
    pacientes_pedido = _obtener_pacientes(db, paciente_ids)
    ocupaciones = repository.listar_ocupaciones(
        db, desde[0], hasta[0]
    )
    pacientes_ocupados = _completar_pacientes_de_ocupaciones(
        db, ocupaciones, pacientes_pedido
    )
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
