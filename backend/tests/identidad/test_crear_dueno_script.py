"""Tests de integración del script que crea el Dueño inicial."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identidad import security
from app.modules.identidad.models import Usuario
from app.modules.identidad.permisos import Rol

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPT = BACKEND_DIR / "scripts" / "crear_dueno.py"


def _env_script(tmp_db_path: str, password: str) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = tmp_db_path
    env["DUENIO_USERNAME"] = "  Duenio  "
    env["DUENIO_PASSWORD"] = password
    env["PYTHONIOENCODING"] = "utf-8"

    pythonpath = env.get("PYTHONPATH")
    if pythonpath:
        env["PYTHONPATH"] = f"{BACKEND_DIR}{os.pathsep}{pythonpath}"
    else:
        env["PYTHONPATH"] = str(BACKEND_DIR)
    return env


def _ejecutar_script(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_script_crear_dueno_es_idempotente_y_no_cambia_el_hash(
    db_session: Session, tmp_db_path: str, password_prueba
) -> None:
    env = _env_script(tmp_db_path, password_prueba)

    primera = _ejecutar_script(env)
    assert primera.returncode == 0, primera.stderr
    assert "Dueño creado: duenio" in primera.stdout

    db_session.expire_all()
    usuarios = db_session.execute(select(Usuario)).scalars().all()
    assert len(usuarios) == 1
    usuario = usuarios[0]
    assert usuario.username == "duenio"
    assert usuario.rol == Rol.DUENIO
    assert usuario.activo is True
    assert usuario.password_hash != password_prueba
    assert security.verificar_password(usuario.password_hash, password_prueba)
    hash_inicial = usuario.password_hash
    db_session.rollback()

    segunda = _ejecutar_script(env)
    assert segunda.returncode == 0, segunda.stderr
    assert "Dueño ya existente: duenio" in segunda.stdout

    db_session.expire_all()
    usuarios = db_session.execute(select(Usuario)).scalars().all()
    assert len(usuarios) == 1
    assert usuarios[0].id == usuario.id
    assert usuarios[0].password_hash == hash_inicial


@pytest.mark.parametrize(
    "faltante",
    ["DUENIO_USERNAME", "DUENIO_PASSWORD", "ambas"],
)
def test_script_sin_variables_devuelve_1(
    tmp_db_path: str, password_prueba, faltante: str
) -> None:
    env = _env_script(tmp_db_path, password_prueba)
    if faltante == "ambas":
        env.pop("DUENIO_USERNAME", None)
        env.pop("DUENIO_PASSWORD", None)
    else:
        env.pop(faltante, None)

    resultado = _ejecutar_script(env)

    assert resultado.returncode == 1
    assert "DUENIO_USERNAME y DUENIO_PASSWORD" in resultado.stderr
