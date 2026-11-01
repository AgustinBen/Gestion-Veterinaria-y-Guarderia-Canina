"""Punto de entrada de la carga del padrón histórico (T-16, RN-50).

Uso desde backend/:
    .\\.venv\\Scripts\\python.exe scripts\\cargar_padron.py
    .\\.venv\\Scripts\\python.exe scripts\\cargar_padron.py --simular

Lee EXCEL_ORIGEN y MIGRACION_SALIDA del entorno o de backend/.env.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.exc import SQLAlchemyError

from app.core import parametros
from app.core.db import SessionLocal, engine
from app.core.parametros import ParametroNoDefinido
from app.modules.migracion.carga import (
    ErrorParametroMigracion,
    cargar_padron,
    resumen_consola,
)
from app.modules.migracion.lector import ErrorEstructuraExcel, ExcelNoEncontrado
from app.modules.migracion.seed import CLAVE_FECHA_CORTE, sembrar_parametros_migracion

try:  # importado como paquete (tests) o ejecutado como script suelto
    from scripts.perfilar_excel import resolver_excel, resolver_salida
except ModuleNotFoundError:  # python scripts/cargar_padron.py
    from perfilar_excel import resolver_excel, resolver_salida


class _ConfigCarga(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    excel_origen: str = "data/planilla.xlsx"
    migracion_salida: str = "data/"


def _mensaje_falta_fecha() -> str:
    """Instrucción concreta para cargar la fecha de corte sin tocar código."""
    return (
        f"Falta el parámetro '{CLAVE_FECHA_CORTE}' (fecha ISO aaaa-mm-dd).\n"
        "Cargalo una vez desde backend/ reemplazando AAAA-MM-DD:\n"
        '  .\\.venv\\Scripts\\python.exe -c "from app.core.db import SessionLocal; '
        "from app.core import parametros; db = SessionLocal(); "
        f"parametros.set_param(db, '{CLAVE_FECHA_CORTE}', 'AAAA-MM-DD', 'str', "
        "modulo='migracion', updated_by='migracion'); db.close()\""
    )


def _fecha_corte_cargada() -> bool:
    """Siembra las claves del módulo (idempotente) y dice si hay fecha de corte."""
    with SessionLocal() as db:
        sembrar_parametros_migracion(db)
        return bool(str(parametros.get_param(db, CLAVE_FECHA_CORTE)).strip())


def main(
    entorno: Mapping[str, str] | None = None,
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Carga el padrón desde el Excel histórico."
    )
    parser.add_argument(
        "--simular",
        action="store_true",
        help="No escribe en la base: deja los archivos *_simulado*.",
    )
    opciones = parser.parse_args(argv)

    try:
        config = _ConfigCarga() if entorno is None else _ConfigCarga(**entorno)
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
        hay_fecha_corte = _fecha_corte_cargada()
    except SQLAlchemyError as exc:
        print(f"Error de base de datos: {exc}", file=sys.stderr)
        return 1
    if not hay_fecha_corte:
        print(_mensaje_falta_fecha(), file=sys.stderr)
        return 4

    try:
        reporte = cargar_padron(
            ruta_excel=ruta_excel,
            salida=directorio_salida,
            engine=engine,
            simular=opciones.simular,
        )
    except ExcelNoEncontrado as exc:
        print(f"Error de entrada: {exc}", file=sys.stderr)
        return 3
    except ErrorEstructuraExcel as exc:
        print(f"Error de estructura del Excel: {exc}", file=sys.stderr)
        return 2
    except (ParametroNoDefinido, ErrorParametroMigracion) as exc:
        print(f"Error de configuración de la migración: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"Error inesperado al cargar: {exc}", file=sys.stderr)
        return 1

    print(resumen_consola(reporte))
    print(f"Salida: {directorio_salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
