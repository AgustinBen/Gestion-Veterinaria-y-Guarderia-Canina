from __future__ import annotations

from decimal import Decimal, InvalidOperation
from time import monotonic
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Configuracion


class ParametroNoDefinido(Exception):
    def __init__(self, clave: str) -> None:
        super().__init__(f"Parámetro no definido: {clave}")
        self.clave = clave


_TIPOS_VALIDOS = {"int", "decimal", "bool", "str"}

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 5.0


def _limpiar_cache() -> None:
    _cache.clear()


def _serializar(valor: Any, tipo: str) -> str:
    if tipo == "int":
        if isinstance(valor, bool):
            raise ValueError("tipo int no acepta bool")
        return str(int(valor))
    if tipo == "decimal":
        if isinstance(valor, Decimal):
            return str(valor)
        return str(Decimal(str(valor)))
    if tipo == "bool":
        if isinstance(valor, bool):
            return "true" if valor else "false"
        s = str(valor).strip().lower()
        if s in {"true", "1", "t", "yes", "y"}:
            return "true"
        if s in {"false", "0", "f", "no", "n"}:
            return "false"
        raise ValueError("valor bool inválido")
    if tipo == "str":
        return str(valor)
    raise ValueError(f"tipo inválido: {tipo}")


def _deserializar(valor: str, tipo: str) -> Any:
    if tipo == "int":
        return int(valor)
    if tipo == "decimal":
        return Decimal(valor)
    if tipo == "bool":
        s = valor.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
        raise ValueError("valor bool inválido")
    if tipo == "str":
        return valor
    raise ValueError(f"tipo inválido: {tipo}")


def get_param(db: Session, clave: str) -> Any:
    ahora = monotonic()
    cached = _cache.get(clave)
    if cached is not None:
        ts, val = cached
        if ahora - ts < _CACHE_TTL:
            return val

    stmt = select(Configuracion).where(Configuracion.clave == clave)
    cfg = db.execute(stmt).scalar_one_or_none()
    if cfg is None:
        raise ParametroNoDefinido(clave)

    if cfg.tipo not in _TIPOS_VALIDOS:
        raise ValueError(f"tipo inválido en configuración: {cfg.tipo}")

    try:
        val = _deserializar(cfg.valor, cfg.tipo)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Error al deserializar parámetro {clave}: {exc}") from exc

    _cache[clave] = (ahora, val)
    return val


def set_param(
    db: Session,
    clave: str,
    valor: Any,
    tipo: str,
    modulo: str | None = None,
    descripcion: str | None = None,
    updated_by: str | None = None,
) -> Configuracion:
    if tipo not in _TIPOS_VALIDOS:
        raise ValueError(f"tipo inválido: {tipo}")

    valor_ser = _serializar(valor, tipo)

    stmt = select(Configuracion).where(Configuracion.clave == clave)
    cfg = db.execute(stmt).scalar_one_or_none()
    if cfg is None:
        cfg = Configuracion(
            clave=clave,
            valor=valor_ser,
            tipo=tipo,
            modulo=modulo,
            descripcion=descripcion,
            updated_by=updated_by,
        )
        db.add(cfg)
    else:
        cfg.valor = valor_ser
        cfg.tipo = tipo
        if modulo is not None:
            cfg.modulo = modulo
        if descripcion is not None:
            cfg.descripcion = descripcion
        if updated_by is not None:
            cfg.updated_by = updated_by

    db.commit()
    db.refresh(cfg)
    _limpiar_cache()
    return cfg


def registrar_parametro(
    db: Session,
    clave: str,
    valor: Any,
    tipo: str,
    modulo: str | None = None,
    descripcion: str | None = None,
    updated_by: str | None = None,
) -> Configuracion:
    # Registrar/crear clave con valor inicial (idempotente si ya existe, no sobreescribe por defecto)
    if tipo not in _TIPOS_VALIDOS:
        raise ValueError(f"tipo inválido: {tipo}")

    stmt = select(Configuracion).where(Configuracion.clave == clave)
    cfg = db.execute(stmt).scalar_one_or_none()
    if cfg is not None:
        return cfg

    valor_ser = _serializar(valor, tipo)
    cfg = Configuracion(
        clave=clave,
        valor=valor_ser,
        tipo=tipo,
        modulo=modulo,
        descripcion=descripcion,
        updated_by=updated_by,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    _limpiar_cache()
    return cfg
