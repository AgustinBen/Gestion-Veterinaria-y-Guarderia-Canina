from datetime import date

import pytest

from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.tramos import TramoInvalido, franjas_del_tramo


def test_tramo_de_una_franja_es_inclusivo() -> None:
    fecha = date(2030, 12, 15)

    assert franjas_del_tramo(fecha, Franja.NOCHE, fecha, Franja.NOCHE) == [
        (fecha, Franja.NOCHE)
    ]


def test_tramo_de_24_horas_incluye_dia_y_noche() -> None:
    fecha = date(2030, 12, 15)

    assert franjas_del_tramo(fecha, Franja.DIA, fecha, Franja.NOCHE) == [
        (fecha, Franja.DIA),
        (fecha, Franja.NOCHE),
    ]


def test_tramo_de_varios_dias_cruza_fin_de_mes() -> None:
    assert franjas_del_tramo(
        date(2030, 12, 31),
        Franja.NOCHE,
        date(2031, 1, 1),
        Franja.DIA,
    ) == [
        (date(2030, 12, 31), Franja.NOCHE),
        (date(2031, 1, 1), Franja.DIA),
    ]


@pytest.mark.parametrize(
    ("desde_fecha", "desde_franja", "hasta_fecha", "hasta_franja"),
    [
        (date(2030, 12, 16), Franja.DIA, date(2030, 12, 15), Franja.NOCHE),
        (date(2030, 12, 15), Franja.NOCHE, date(2030, 12, 15), Franja.DIA),
    ],
)
def test_tramo_invertido_lanza_error(
    desde_fecha: date,
    desde_franja: Franja,
    hasta_fecha: date,
    hasta_franja: Franja,
) -> None:
    with pytest.raises(TramoInvalido):
        franjas_del_tramo(desde_fecha, desde_franja, hasta_fecha, hasta_franja)
