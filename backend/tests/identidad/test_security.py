"""Tests de hash argon2 y tokens JWT."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest

from app.core.config import get_settings
from app.modules.identidad.permisos import Rol
from app.modules.identidad.security import (
    TokenInvalido,
    crear_token,
    decodificar_token,
    hash_password,
    verificar_password,
)

BASE = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
EXP_FUTURA = int((BASE + timedelta(minutes=5)).timestamp())


def _decodificar_sin_vencimiento(token: str) -> dict[str, Any]:
    payload: dict[str, Any] = jwt.decode(
        token,
        get_settings().secret_key,
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False, "verify_nbf": False},
    )
    return payload


# --- Contraseñas ---------------------------------------------------------


def test_hash_no_guarda_texto_plano() -> None:
    password = "clave-de-prueba-segura"

    hasheada = hash_password(password)

    assert hasheada != password
    assert password not in hasheada
    assert hasheada.startswith("$argon2")
    assert verificar_password(hasheada, password) is True


def test_hash_usa_salt() -> None:
    password = "clave-de-prueba-segura"

    primera = hash_password(password)
    segunda = hash_password(password)

    assert primera != segunda
    assert verificar_password(primera, password) is True
    assert verificar_password(segunda, password) is True


def test_password_incorrecta_no_verifica() -> None:
    hasheada = hash_password("clave-correcta")

    assert verificar_password(hasheada, "clave-incorrecta") is False


def test_hash_invalido_no_verifica() -> None:
    assert verificar_password("esto-no-es-un-hash-argon2", "clave") is False


# --- Tokens -------------------------------------------------------------


def test_token_roundtrip_con_reloj_inyectado() -> None:
    token = crear_token(7, Rol.PERSONAL, ahora=BASE)

    payload = decodificar_token(token, ahora=BASE)

    assert payload.usuario_id == 7
    assert payload.rol is Rol.PERSONAL


def test_decodificar_usa_el_reloj_inyectado_y_no_el_real() -> None:
    # Un token emitido en 2020 ya estaría vencido según el reloj real.
    base = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)
    token = crear_token(3, Rol.DUENIO, ahora=base)

    payload = decodificar_token(token, ahora=base)

    assert payload.usuario_id == 3
    assert payload.rol is Rol.DUENIO


def test_token_usa_session_minutes_de_settings() -> None:
    token = crear_token(7, Rol.VETERINARIO, ahora=BASE)

    payload = _decodificar_sin_vencimiento(token)
    vencimiento_esperado = int(
        (BASE + timedelta(minutes=get_settings().session_minutes)).timestamp()
    )

    assert payload["exp"] == vencimiento_esperado


def test_token_vence_en_el_borde_exacto() -> None:
    token = crear_token(7, Rol.PERSONAL, ahora=BASE)
    vencimiento = BASE + timedelta(minutes=get_settings().session_minutes)

    valido = decodificar_token(token, ahora=vencimiento - timedelta(seconds=1))

    assert valido.usuario_id == 7

    with pytest.raises(TokenInvalido):
        decodificar_token(token, ahora=vencimiento)


def test_token_vencido_es_invalido() -> None:
    token = crear_token(7, Rol.PERSONAL, ahora=BASE)

    with pytest.raises(TokenInvalido):
        decodificar_token(
            token,
            ahora=BASE + timedelta(minutes=get_settings().session_minutes, seconds=1),
        )


def test_token_alterado_es_invalido() -> None:
    token = crear_token(7, Rol.PERSONAL, ahora=BASE)
    cabecera, payload, firma = token.split(".")
    primer_caracter = "A" if firma[0] != "A" else "B"
    alterado = f"{cabecera}.{payload}.{primer_caracter}{firma[1:]}"

    with pytest.raises(TokenInvalido):
        decodificar_token(alterado, ahora=BASE)


def test_token_firmado_con_otra_clave_es_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    token = crear_token(7, Rol.PERSONAL, ahora=BASE)

    monkeypatch.setattr(
        get_settings(),
        "secret_key",
        "otra-clave-de-pruebas-con-mas-de-32-bytes",
    )

    with pytest.raises(TokenInvalido):
        decodificar_token(token, ahora=BASE)


def test_token_malformado_es_invalido() -> None:
    with pytest.raises(TokenInvalido):
        decodificar_token("esto-no-es-un-jwt", ahora=BASE)


def test_token_no_contiene_password() -> None:
    token = crear_token(7, Rol.DUENIO, ahora=BASE)

    payload = _decodificar_sin_vencimiento(token)

    assert set(payload) == {"sub", "rol", "exp"}


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": "1", "rol": "DUENIO"},
        {"rol": "DUENIO", "exp": EXP_FUTURA},
        {"sub": "1", "exp": EXP_FUTURA},
    ],
)
def test_token_sin_claims_requeridos_es_invalido(payload: dict[str, Any]) -> None:
    token = jwt.encode(payload, get_settings().secret_key, algorithm="HS256")

    with pytest.raises(TokenInvalido):
        decodificar_token(token, ahora=BASE)


@pytest.mark.parametrize(
    ("claim", "valor"),
    [
        ("sub", "no-es-un-numero"),
        ("sub", "0"),
        ("sub", "-1"),
        ("rol", "ROOT"),
        ("rol", "duenio"),
        ("exp", "no-es-una-fecha"),
        ("exp", True),
    ],
)
def test_token_con_claims_invalidos_es_invalido(claim: str, valor: Any) -> None:
    payload: dict[str, Any] = {
        "sub": "1",
        "rol": "DUENIO",
        "exp": int((BASE + timedelta(minutes=5)).timestamp()),
    }
    payload[claim] = valor
    token = jwt.encode(payload, get_settings().secret_key, algorithm="HS256")

    with pytest.raises(TokenInvalido):
        decodificar_token(token, ahora=BASE)
