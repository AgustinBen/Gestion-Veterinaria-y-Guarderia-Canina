"""Utilidades para trabajar con dinero en centavos."""

from __future__ import annotations


class DineroError(Exception):
    """Error de validación de valores monetarios."""


def a_centavos(valor: int) -> int:
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise DineroError("El monto debe ser un entero en centavos")
    if valor < 0:
        raise DineroError("El monto no puede ser negativo")
    return valor


def validar_positivo(valor: int) -> int:
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise DineroError("El monto debe ser un entero en centavos")
    if valor <= 0:
        raise DineroError("El monto debe ser mayor a 0")
    return valor


def formatear_pesos(centavos: int) -> str:
    centavos_validados = a_centavos(centavos)
    signo = "-" if centavos_validados < 0 else ""
    absoluto = abs(centavos_validados)
    pesos = absoluto // 100
    cent = absoluto % 100
    return f"{signo}${pesos}.{cent:02d}"
