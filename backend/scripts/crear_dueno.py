"""Crea el usuario Dueño inicial a partir de variables de entorno.

Uso:
    DUENIO_USERNAME=duenio DUENIO_PASSWORD=... python scripts/crear_dueno.py

Es idempotente: si el username ya existe con rol DUENIO, no lo modifica.
Si existe con otro rol, termina con código 1.
"""

from __future__ import annotations

import os
import sys

from app.core.db import SessionLocal
from app.modules.identidad import service


def main() -> int:
    username = os.environ.get("DUENIO_USERNAME", "").strip()
    password = os.environ.get("DUENIO_PASSWORD", "")

    if not username or not password:
        print(
            "Definí DUENIO_USERNAME y DUENIO_PASSWORD en el entorno.",
            file=sys.stderr,
        )
        return 1

    with SessionLocal() as db:
        try:
            usuario, creado = service.crear_dueno_inicial(db, username, password)
        except service.UsuarioExistenteNoDuenio:
            print(
                f"El usuario '{username}' ya existe con otro rol.",
                file=sys.stderr,
            )
            return 1
        except service.UsernameDuplicado:
            print("El username ya está registrado.", file=sys.stderr)
            return 1
        except service.DatosInvalidos as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if creado:
        print(f"Dueño creado: {usuario.username}")
    else:
        print(f"Dueño ya existente: {usuario.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
