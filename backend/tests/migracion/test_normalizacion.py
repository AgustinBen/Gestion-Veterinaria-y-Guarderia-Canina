"""Normalización pura de la hoja Clientes_y_Mascotas (T-16, Fase A)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.modules.migracion import normalizacion
from app.modules.migracion.normalizacion import NormalizadorTelefono

CORTE = date(2026, 10, 1)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("3 años", 36),
        ("4", 48),
        ("8 meses", 8),
        ("2 años y medio", 30),
        ("3 años aprox", 36),
        ("1 año", 12),
        ("10", 120),
        ("", None),
        ("no sé", None),
    ],
)
def test_edad_a_meses(texto: str, esperado: int | None) -> None:
    assert normalizacion.edad_a_meses(texto) == esperado


@pytest.mark.parametrize(
    ("meses", "esperado"),
    [
        (36, date(2023, 10, 1)),
        (8, date(2026, 2, 1)),
        (0, CORTE),
    ],
)
def test_fecha_nacimiento_aprox_desde_el_corte(meses: int, esperado: date) -> None:
    assert normalizacion.fecha_nacimiento_aprox(CORTE, meses) == esperado


def test_fecha_nacimiento_aprox_conserva_el_dia_del_corte() -> None:
    assert normalizacion.fecha_nacimiento_aprox(date(2026, 1, 31), 1) == date(
        2025, 12, 31
    )


def test_fecha_nacimiento_aprox_rechaza_edades_negativas() -> None:
    with pytest.raises(ValueError):
        normalizacion.fecha_nacimiento_aprox(CORTE, -1)


@pytest.mark.parametrize(
    "texto",
    [
        "12/03/2024",
        "2024-03-12",
        "12 de marzo 2024",
        "12 de marzo de 2024",
        "12/03/24",
    ],
)
def test_fecha_acepta_los_cuatro_formatos(texto: str) -> None:
    assert normalizacion.fecha(texto) == date(2024, 3, 12)


def test_fecha_imposible_no_se_inventa() -> None:
    assert normalizacion.fecha("31/02/2024") is None
    assert normalizacion.fecha("ayer") is None
    assert normalizacion.fecha("") is None


def test_peso_con_coma_equivale_a_punto() -> None:
    assert normalizacion.peso_kg("12,5 kg") == Decimal("12.5")
    assert normalizacion.peso_kg("12.5") == Decimal("12.5")
    assert normalizacion.peso_kg("") is None


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("11 4455-8899", "1144558899"),
        ("+5491144558899", "1144558899"),
        ("15-6677-2233", "1166772233"),
        ("011 6677-2233", "1166772233"),
        ("011 4890-1122", "1148901122"),
        ("+54 9 11 3322 1100", "1133221100"),
        ("0341-155443322", "3415443322"),
    ],
)
def test_telefono_con_los_ejemplos_de_migracion_md(
    normalizador_telefono: NormalizadorTelefono, texto: str, esperado: str
) -> None:
    assert normalizacion.telefono(texto, normalizador_telefono) == esperado


@pytest.mark.parametrize(
    "texto",
    ["Sin telefono (dejo mail)", "sin teléfono", "", "   "],
)
def test_telefono_sin_numero_es_sin_telefono(
    normalizador_telefono: NormalizadorTelefono, texto: str
) -> None:
    assert (
        normalizacion.telefono(texto, normalizador_telefono)
        == normalizacion.SIN_TELEFONO
    )


@pytest.mark.parametrize(
    "texto",
    ["11 5555-1234 / 11 6666-5678", "no atiende", "123"],
)
def test_telefono_no_reconocible_va_a_revision(
    normalizador_telefono: NormalizadorTelefono, texto: str
) -> None:
    assert (
        normalizacion.telefono(texto, normalizador_telefono)
        == normalizacion.REVISION
    )


def test_quita_titulo_y_el_ultimo_termino_es_el_apellido() -> None:
    assert normalizacion.limpiar_nombre_dueno("Dr. Carlos Tevez") == (
        "Carlos",
        "Tevez",
        "Dr.",
    )
    assert normalizacion.limpiar_nombre_dueno("Dra. Laura") == ("Laura", None, "Dra.")


def test_un_solo_termino_queda_para_revision() -> None:
    nombre, apellido, titulo = normalizacion.limpiar_nombre_dueno("Lucia")
    assert (nombre, apellido, titulo) == ("Lucia", None, None)


def test_nombre_guardado_capitaliza_sin_perder_tildes() -> None:
    assert normalizacion.limpiar_nombre_dueno("VALERIA GOMEZ") == (
        "Valeria",
        "Gomez",
        None,
    )
    assert normalizacion.limpiar_nombre_dueno("MARÍA JOSÉ PÉREZ") == (
        "María José",
        "Pérez",
        None,
    )


def test_claves_de_comparacion_ignoran_tildes_y_mayusculas() -> None:
    assert normalizacion.claves_de_comparacion("María", "Gómez") == (
        "maria",
        "gomez",
    )
    assert normalizacion.claves_de_comparacion("MARIA", "GOMEZ") == (
        "maria",
        "gomez",
    )
    assert normalizacion.claves_de_comparacion("Maria", "Gomez") != (
        "maria",
        "gonzalez",
    )


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Perro - Labrador", ("Perro", "Labrador", None)),
        ("canino", ("Perro", None, None)),
        ("Gata Siamesa", ("Gato", "Siames", None)),
        ("Gato - Siames", ("Gato", "Siames", None)),
        ("Perro - Caniche", ("Perro", "Caniche", None)),
        ("Mestizo mediano", (None, "Mestizo", "Mediano")),
        ("", (None, None, None)),
    ],
)
def test_especie_raza_por_diccionario(
    texto: str, esperado: tuple[str | None, str | None, str | None]
) -> None:
    assert normalizacion.especie_raza(texto) == esperado


def test_sin_especie_explicita_nunca_se_asume() -> None:
    especie, _, tamanio = normalizacion.especie_raza("Mestizo mediano")
    assert especie is None
    assert tamanio == "Mediano"
