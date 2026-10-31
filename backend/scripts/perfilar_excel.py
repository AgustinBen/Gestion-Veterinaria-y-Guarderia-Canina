"""Punto de entrada del perfilado del Excel histórico (T-15).

Uso desde backend/:
    .\\.venv\\Scripts\\python.exe scripts\\perfilar_excel.py

Lee EXCEL_ORIGEN y MIGRACION_SALIDA del entorno o de backend/.env.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.modules.migracion.lector import ErrorEstructuraExcel, ExcelNoEncontrado
from app.modules.migracion.perfilado import ErrorSinDatos, perfilar, resumen_consola


class _ConfigPerfilado(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    excel_origen: str = "data/planilla.xlsx"
    migracion_salida: str = "data/"


def resolver_excel(origen: str) -> Path:
    """Resuelve el archivo de origen; acepta un .xlsx o un directorio con uno solo."""
    ruta = Path(origen)
    if ruta.is_file():
        if ruta.suffix.lower() != ".xlsx":
            raise ExcelNoEncontrado(f"El archivo de origen no es .xlsx: {ruta}")
        return ruta

    if ruta.is_dir():
        candidatos = sorted(
            candidato
            for candidato in ruta.glob("*.xlsx")
            if not candidato.name.startswith("~$")
        )
        if len(candidatos) == 1:
            return candidatos[0]
        if not candidatos:
            raise ExcelNoEncontrado(
                f"No se encontró ningún .xlsx en el directorio: {ruta}"
            )
        nombres = ", ".join(candidato.name for candidato in candidatos)
        raise ExcelNoEncontrado(
            f"Hay más de un .xlsx en '{ruta}': {nombres}. Indicá EXCEL_ORIGEN con el archivo."
        )

    raise ExcelNoEncontrado(f"No se encontró el archivo Excel: {ruta}")


def resolver_salida(salida: str) -> Path:
    ruta = Path(salida)
    if ruta.exists() and not ruta.is_dir():
        raise ValueError(f"La salida debe ser un directorio: {ruta}")
    return ruta


def main(entorno: Mapping[str, str] | None = None) -> int:
    try:
        config = _ConfigPerfilado() if entorno is None else _ConfigPerfilado(**entorno)
    except Exception as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 1

    try:
        ruta_excel = resolver_excel(config.excel_origen)
        directorio_salida = resolver_salida(config.migracion_salida)
    except ExcelNoEncontrado as exc:
        print(f"Error de entrada: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError) as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 1

    try:
        reporte = perfilar(ruta_excel, directorio_salida)
    except ErrorEstructuraExcel as exc:
        print(f"Error de estructura del Excel: {exc}", file=sys.stderr)
        return 2
    except ExcelNoEncontrado as exc:
        print(f"Error de entrada: {exc}", file=sys.stderr)
        return 3
    except ErrorSinDatos as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"Error inesperado al perfilar: {exc}", file=sys.stderr)
        return 1

    print(resumen_consola(reporte))
    print(f"Salida: {directorio_salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
