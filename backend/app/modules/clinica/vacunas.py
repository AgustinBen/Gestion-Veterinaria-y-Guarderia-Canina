"""Cálculo de estado de vacunas para la libreta clínica."""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.clinica.schemas import EstadoVacuna


def estado_vacuna(
    proxima_dosis: date | None,
    *,
    hoy: date,
    dias_aviso: int,
) -> EstadoVacuna:
    if dias_aviso < 0:
        raise ValueError("clinica.dias_aviso_vacuna no puede ser negativo")
    if proxima_dosis is None:
        return EstadoVacuna.VIGENTE
    if proxima_dosis < hoy:
        return EstadoVacuna.VENCIDA
    if proxima_dosis <= hoy + timedelta(days=dias_aviso):
        return EstadoVacuna.POR_VENCER
    return EstadoVacuna.VIGENTE
