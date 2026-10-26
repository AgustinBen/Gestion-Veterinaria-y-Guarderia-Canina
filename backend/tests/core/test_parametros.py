from decimal import Decimal

import pytest

from app.core import parametros
from app.core.parametros import ParametroNoDefinido, get_param, set_param


def test_get_param_tipos_correctos(db_session, sembrar_config):
    parametros._limpiar_cache()
    sembrar_config("p_int", 5, "int")
    sembrar_config("p_dec", Decimal("10.50"), "decimal")
    sembrar_config("p_bool", True, "bool")
    sembrar_config("p_str", "hola", "str")

    assert get_param(db_session, "p_int") == 5
    assert isinstance(get_param(db_session, "p_int"), int)
    assert get_param(db_session, "p_dec") == Decimal("10.50")
    assert isinstance(get_param(db_session, "p_dec"), Decimal)
    assert get_param(db_session, "p_bool") is True
    assert isinstance(get_param(db_session, "p_bool"), bool)
    assert get_param(db_session, "p_str") == "hola"
    assert isinstance(get_param(db_session, "p_str"), str)


def test_clave_inexistente_lanza_parametro_no_definido(db_session):
    parametros._limpiar_cache()
    with pytest.raises(ParametroNoDefinido):
        get_param(db_session, "no_existe")


def test_set_param_actualiza_y_se_lee_aunque_haya_cache(db_session, sembrar_config):
    parametros._limpiar_cache()
    sembrar_config("p_int", 1, "int")
    v1 = get_param(db_session, "p_int")
    assert v1 == 1
    set_param(db_session, "p_int", 2, "int")
    v2 = get_param(db_session, "p_int")
    assert v2 == 2


def test_valor_decimal_no_pierde_precision(db_session, sembrar_config):
    parametros._limpiar_cache()
    sembrar_config("p_dec", Decimal("123.456789"), "decimal")
    v = get_param(db_session, "p_dec")
    assert v == Decimal("123.456789")


def test_aislamiento_entre_tests_1(db_session, sembrar_config):
    parametros._limpiar_cache()
    sembrar_config("aislado", 1, "int")
    assert get_param(db_session, "aislado") == 1


def test_aislamiento_entre_tests_2(db_session):
    parametros._limpiar_cache()
    with pytest.raises(ParametroNoDefinido):
        get_param(db_session, "aislado")
