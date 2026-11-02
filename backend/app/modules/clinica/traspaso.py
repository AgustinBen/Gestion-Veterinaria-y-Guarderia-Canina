"""Cálculo puro de ventanas de traspaso entre turnos de personal."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.modules.clinica.models import FranjaTurnoPersonal
from app.modules.clinica.schemas import EmpleadoTraspaso, VentanaTraspasoOut


@dataclass(frozen=True)
class TurnoDefinidoConPersonal:
    fecha: date
    turno: FranjaTurnoPersonal
    hora_desde: time
    hora_hasta: time
    empleados: tuple[EmpleadoTraspaso, ...]


def _fin_turno(turno: TurnoDefinidoConPersonal) -> datetime:
    inicio = datetime.combine(turno.fecha, turno.hora_desde)
    fin = datetime.combine(turno.fecha, turno.hora_hasta)
    if fin <= inicio:
        fin += timedelta(days=1)
    return fin


def ventanas_traspaso(
    dia: date,
    definicion: tuple[TurnoDefinidoConPersonal, ...] | list[TurnoDefinidoConPersonal],
    minutos: int,
) -> list[VentanaTraspasoOut]:
    if minutos < 0:
        raise ValueError("Los minutos de traspaso no pueden ser negativos")
    if minutos == 0:
        return []

    por_fecha_turno = {(item.fecha, item.turno): item for item in definicion}
    anterior = dia - timedelta(days=1)
    cambios = (
        (FranjaTurnoPersonal.MANANA, dia, FranjaTurnoPersonal.TARDE, dia),
        (FranjaTurnoPersonal.TARDE, dia, FranjaTurnoPersonal.NOCHE, dia),
        (FranjaTurnoPersonal.NOCHE, anterior, FranjaTurnoPersonal.MANANA, dia),
    )
    ventanas: list[VentanaTraspasoOut] = []
    duracion = timedelta(minutes=minutos)

    for sale, fecha_sale, entra, fecha_entra in cambios:
        turno_saliente = por_fecha_turno.get((fecha_sale, sale))
        turno_entrante = por_fecha_turno.get((fecha_entra, entra))
        if turno_saliente is None or turno_entrante is None:
            continue
        fin = _fin_turno(turno_saliente)
        ventanas.append(
            VentanaTraspasoOut(
                inicio=fin - duracion,
                fin=fin,
                turno_sale=sale,
                turno_entra=entra,
                empleados_salen=list(turno_saliente.empleados),
                empleados_entran=list(turno_entrante.empleados),
            )
        )
    return ventanas
