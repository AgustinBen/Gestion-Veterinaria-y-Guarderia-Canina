#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from pathlib import Path

# Asegurar que el backend esté en el path
BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.modules.migracion import perfilado  # noqa: E402


def main() -> int:
    excel_origen = os.environ.get("EXCEL_ORIGEN")
    salida_dir = os.environ.get("MIGRACION_SALIDA", "data")
    try:
        if excel_origen:
            ruta = excel_origen
        else:
            # buscar en data/
            data_dir = Path("data")
            if not data_dir.exists():
                data_dir = BACKEND_DIR / "data"
            candidatos = sorted(data_dir.glob("*.xlsx")) if data_dir.exists() else []
            if not candidatos:
                print("No se encontró archivo .xlsx. Definí EXCEL_ORIGEN o colocá el archivo en data/", file=sys.stderr)
                return 1
            ruta = str(candidatos[0])
        perfilado.perfilar_excel(ruta, salida_dir)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
