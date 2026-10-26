"""Hash de contraseñas y tokens JWT del módulo identidad."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.modules.identidad.permisos import Rol

_ALGORITMO = "HS256"
_hasher = PasswordHasher()


class TokenInvalido(Exception):
    """El token falta, está vencido, fue alterado o tiene claims inválidos."""


@dataclass(frozen=True)
class TokenPayload:
    usuario_id: int
    rol: Rol


def hash_password(password: str) -> str:
    """Devuelve el hash argon2 de la contraseña."""
    return _hasher.hash(password)


def verificar_password(password_hash: str, password: str) -> bool:
    """Compara una contraseña con su hash. Un hash ilegible no autentica."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _normalizar_ahora(ahora: datetime | None) -> datetime:
    if ahora is None:
        return datetime.now(timezone.utc)
    if ahora.tzinfo is None:
        return ahora.replace(tzinfo=timezone.utc)
    return ahora.astimezone(timezone.utc)


def crear_token(usuario_id: int, rol: Rol, ahora: datetime | None = None) -> str:
    """Crea un JWT con vencimiento configurable desde Settings."""
    settings = get_settings()
    momento = _normalizar_ahora(ahora)
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "rol": rol.value,
        "exp": momento + timedelta(minutes=settings.session_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITMO)


def decodificar_token(token: str, ahora: datetime | None = None) -> TokenPayload:
    """Valida firma, claims y vencimiento contra el reloj inyectado.

    PyJWT valida la firma pero no el ``exp``: la comparación temporal se hace
    acá para poder testear tokens vencidos sin esperar.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_ALGORITMO],
            options={
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "require": ["exp", "sub", "rol"],
            },
        )
    except jwt.InvalidTokenError as exc:
        raise TokenInvalido("Token inválido") from exc

    exp = payload.get("exp")
    if isinstance(exp, bool) or not isinstance(exp, (int, float)):
        raise TokenInvalido("Token sin vencimiento válido")
    vencimiento = datetime.fromtimestamp(exp, tz=timezone.utc)
    if vencimiento <= _normalizar_ahora(ahora):
        raise TokenInvalido("Token vencido")

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise TokenInvalido("Token sin usuario válido")
    try:
        usuario_id = int(sub)
    except ValueError as exc:
        raise TokenInvalido("Token sin usuario válido") from exc
    if usuario_id <= 0:
        raise TokenInvalido("Token sin usuario válido")

    rol_raw = payload.get("rol")
    if not isinstance(rol_raw, str):
        raise TokenInvalido("Token sin rol válido")
    try:
        rol = Rol(rol_raw)
    except ValueError as exc:
        raise TokenInvalido("Token sin rol válido") from exc

    return TokenPayload(usuario_id=usuario_id, rol=rol)
