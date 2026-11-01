import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


def _alembic(
    backend_dir: Path, env: dict[str, str], *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
    )


def _unico_hoja_fila(insp) -> bool:
    return any(
        unico["column_names"] == ["hoja", "fila"]
        for unico in insp.get_unique_constraints("migracion_registro")
    )


def test_migracion_0006_crea_y_elimina_registro(tmp_path):
    db_path = tmp_path / "test_mig.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    backend_dir = Path(__file__).resolve().parents[2]

    res = _alembic(backend_dir, env, "upgrade", "head")
    assert res.returncode == 0, res.stdout + res.stderr
    engine = create_engine(f"sqlite:///{db_path}")
    insp = inspect(engine)
    assert "migracion_registro" in insp.get_table_names()
    assert _unico_hoja_fila(insp)
    columnas = {columna["name"] for columna in insp.get_columns("migracion_registro")}
    assert {
        "hoja",
        "fila",
        "id_origen",
        "hash_fila",
        "texto_original",
        "estado",
        "motivo",
    } <= columnas

    res2 = _alembic(backend_dir, env, "downgrade", "0005")
    assert res2.returncode == 0, res2.stdout + res2.stderr
    insp2 = inspect(engine)
    insp2.clear_cache()
    assert "migracion_registro" not in insp2.get_table_names()

    res3 = _alembic(backend_dir, env, "upgrade", "head")
    assert res3.returncode == 0, res3.stdout + res3.stderr
    engine3 = create_engine(f"sqlite:///{db_path}")
    insp3 = inspect(engine3)
    assert "migracion_registro" in insp3.get_table_names()
    assert _unico_hoja_fila(insp3)
    engine.dispose()
    engine3.dispose()
