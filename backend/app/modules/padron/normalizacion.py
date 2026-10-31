"""Normalización de datos del padrón (RN-01, RN-02 y RN-06)."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

from app.core import parametros

CLAVE_CODIGO_AREA_DEFECTO = "padron.codigo_area_defecto"
CLAVE_UMBRAL_NOMBRE_PARECIDO = "padron.umbral_nombre_parecido"

_NO_DIGITOS = re.compile(r"\D+")


class TelefonoInvalido(ValueError):
    """El teléfono no se puede normalizar al formato único de 10 dígitos."""


def normalizar_texto(texto: str) -> str:
    """Texto comparable: sin tildes, sin mayúsculas y con espacios simples."""
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )
    return " ".join(sin_tildes.casefold().split())


def formatear_nombre(texto: str) -> str:
    """Nombre para guardar: espacios simples y cada palabra capitalizada."""
    limpio = " ".join(texto.split())
    return " ".join(parte.capitalize() for parte in limpio.split(" "))


def normalizar_dni(dni: str | None) -> str | None:
    """El DNI se guarda solo con dígitos; vacío equivale a ausente."""
    if dni is None:
        return None
    digitos = _NO_DIGITOS.sub("", dni)
    return digitos or None


def normalizar_telefono(numero: str, codigo_area_defecto: str) -> str:
    """Normaliza a 10 dígitos según la spec de padrón.

    Quita el 54 inicial, el 9 de móvil, el 0 inicial y el 15 de móvil
    (después del código de área o al inicio cuando el número viene sin
    código de área). Si quedan 8 dígitos, antepone el código de área por
    defecto configurado.
    """
    digitos = _NO_DIGITOS.sub("", numero or "")
    if not digitos:
        raise TelefonoInvalido("El teléfono no puede estar vacío")

    if digitos.startswith("54"):
        digitos = digitos[2:]
    if digitos.startswith("9"):
        digitos = digitos[1:]
    if digitos.startswith("0"):
        digitos = digitos[1:]
    if len(digitos) == 10 and digitos.startswith("15"):
        # Número móvil escrito sin código de área: "15-6677-2233".
        digitos = digitos[2:]
    if len(digitos) == 12:
        for indice in (2, 3, 4):
            if digitos[indice : indice + 2] == "15":
                digitos = digitos[:indice] + digitos[indice + 2 :]
                break

    if len(digitos) == 8:
        digitos = f"{codigo_area_defecto}{digitos}"

    if len(digitos) != 10:
        raise TelefonoInvalido("El teléfono debe tener 10 dígitos")
    return digitos


def codigo_area_defecto(db: Session) -> str:
    """Código de área configurable que completa los teléfonos de 8 dígitos."""
    return str(parametros.get_param(db, CLAVE_CODIGO_AREA_DEFECTO))


def umbral_nombre_parecido(db: Session) -> float:
    """Umbral configurable de similitud para avisar por nombre parecido."""
    return float(parametros.get_param(db, CLAVE_UMBRAL_NOMBRE_PARECIDO))
