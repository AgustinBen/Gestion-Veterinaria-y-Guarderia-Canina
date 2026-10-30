from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core import parametros
from app.core.models import Configuracion
from app.core.parametros import ParametroNoDefinido, get_param, set_param
from app.modules.guarderia.seed import (
    CUPO_MAXIMO_INICIAL,
    DESCUENTO_MULTIMASCOTA_PCT_INICIAL,
    PLAZAS_EMERGENCIA_INICIAL,
    RESERVA_MAX_MESES_INICIAL,
    sembrar_parametros,
)


@pytest.fixture(autouse=True)
def limpiar_cache_parametros() -> Generator[None, None, None]:
    parametros._limpiar_cache()
    yield
    parametros._limpiar_cache()


def test_sembrar_parametros_crea_valores_con_tipos_correctos(db_session) -> None:
    sembrar_parametros(db_session)

    cupo = get_param(db_session, "guarderia.cupo_maximo")
    plazas_emergencia = get_param(db_session, "guarderia.plazas_emergencia")
    reserva_max_meses = get_param(db_session, "guarderia.reserva_max_meses")
    descuento = get_param(db_session, "guarderia.descuento_multimascota_pct")

    assert cupo == CUPO_MAXIMO_INICIAL
    assert isinstance(cupo, int)
    assert plazas_emergencia == PLAZAS_EMERGENCIA_INICIAL
    assert isinstance(plazas_emergencia, int)
    assert reserva_max_meses == RESERVA_MAX_MESES_INICIAL
    assert isinstance(reserva_max_meses, int)
    assert descuento == DESCUENTO_MULTIMASCOTA_PCT_INICIAL
    assert isinstance(descuento, Decimal)


def test_sembrar_dos_veces_no_duplica_ni_pisa_cambios(db_session) -> None:
    sembrar_parametros(db_session)
    set_param(db_session, "guarderia.cupo_maximo", CUPO_MAXIMO_INICIAL - 2, "int")

    sembrar_parametros(db_session)
    sembrar_parametros(db_session)

    assert get_param(db_session, "guarderia.cupo_maximo") == CUPO_MAXIMO_INICIAL - 2
    assert (
        db_session.execute(
            select(func.count(Configuracion.id)).where(
                Configuracion.clave == "guarderia.cupo_maximo"
            )
        ).scalar_one()
        == 1
    )


def test_no_se_siembra_parametro_de_sena_minima(db_session) -> None:
    sembrar_parametros(db_session)

    with pytest.raises(ParametroNoDefinido):
        get_param(db_session, "guarderia.sena_minima")


def test_arranque_de_app_siembra_parametros_en_su_base(
    db_session, engine_sqlite, monkeypatch
) -> None:
    import app.main as main

    session_local = sessionmaker(bind=engine_sqlite, future=True)
    monkeypatch.setattr(main, "SessionLocal", session_local)

    with TestClient(main.app):
        with session_local() as session:
            assert get_param(session, "guarderia.cupo_maximo") == CUPO_MAXIMO_INICIAL
