"""Teléfono del padrón: normalización oficial y su puerta pública para migración."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.modules.padron import service


@pytest.mark.parametrize(
    ("entrada", "esperado"),
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
def test_normalizar_telefono_da_los_ejemplos_de_la_spec(
    db_session: Session, entrada: str, esperado: str
) -> None:
    assert service.normalizar_telefono(db_session, entrada) == esperado


@pytest.mark.parametrize(
    "entrada",
    ["Sin telefono (dejo mail)", "", "123", "11 5555-1234 / 11 6666-5678"],
)
def test_normalizar_telefono_invalido_es_datos_invalidos(
    db_session: Session, entrada: str
) -> None:
    with pytest.raises(service.DatosInvalidos):
        service.normalizar_telefono(db_session, entrada)
