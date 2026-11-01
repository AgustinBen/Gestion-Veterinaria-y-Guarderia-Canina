"""Funciones puras para expandir tramos de guardería."""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.guarderia.franjas import Franja


class TramoInvalido(ValueError):
    """El fin del tramo es anterior a su inicio."""


def franjas_del_tramo(
    desde_fecha: date,
    desde_franja: Franja,
    hasta_fecha: date,
    hasta_franja: Franja,
) -> list[tuple[date, Franja]]:
    """Expande un tramo inclusivo, ordenando DIA antes que NOCHE."""
    invertido = desde_fecha > hasta_fecha or (
        desde_fecha == hasta_fecha
        and desde_franja == Franja.NOCHE
        and hasta_franja == Franja.DIA
    )
    if invertido:
        raise TramoInvalido("El fin del tramo es anterior al inicio")

    franjas: list[tuple[date, Franja]] = []
    fecha = desde_fecha
    franja = desde_franja
    while True:
        franjas.append((fecha, franja))
        if fecha == hasta_fecha and franja == hasta_franja:
            return franjas
        if franja == Franja.DIA:
            franja = Franja.NOCHE
        else:
            fecha += timedelta(days=1)
            franja = Franja.DIA
