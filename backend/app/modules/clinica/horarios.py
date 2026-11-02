"""Validación de franjas de atención veterinaria."""

from collections.abc import Iterable
from datetime import time

from app.modules.clinica.schemas import HorarioAtencionIn


def validar_horarios(horarios: Iterable[HorarioAtencionIn]) -> None:
    por_dia: dict[int, list[tuple[time, time]]] = {}
    for horario in horarios:
        if horario.hora_desde >= horario.hora_hasta:
            raise ValueError("La hora desde debe ser menor que la hora hasta")
        por_dia.setdefault(horario.dia_semana, []).append(
            (horario.hora_desde, horario.hora_hasta)
        )

    for franjas in por_dia.values():
        franjas.sort()
        if any(actual[0] < anterior[1] for anterior, actual in zip(franjas, franjas[1:])):
            raise ValueError("Las franjas del mismo día no pueden superponerse")
