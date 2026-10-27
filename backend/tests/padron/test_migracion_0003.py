import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def test_migracion_upgrade_downgrade_y_seeds(tmp_path):
    db_path = tmp_path / "test_mig.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    backend_dir = Path(__file__).resolve().parents[2]
    # upgrade
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    engine = create_engine(f"sqlite:///{db_path}")
    insp = inspect(engine)
    assert "persona" in insp.get_table_names()
    assert "paciente" in insp.get_table_names()
    assert "empleado" in insp.get_table_names()
    with engine.begin() as conn:
        r = conn.execute(text("SELECT nombre FROM especie ORDER BY id"))
        assert [x[0] for x in r] == ["Perro", "Gato"]
    # downgrade
    res2 = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 0, res2.stdout + res2.stderr
    insp2 = inspect(engine)
    # after downgrade base, tables from migrations gone (config/usuario/padron)
    assert "persona" not in insp2.get_table_names()
    # upgrade again
    res3 = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res3.returncode == 0, res3.stdout + res3.stderr
    engine3 = create_engine(f"sqlite:///{db_path}")
    insp3 = inspect(engine3)
    assert "persona" in insp3.get_table_names()
    with engine3.begin() as conn:
        r = conn.execute(text("SELECT nombre FROM especie ORDER BY id"))
        assert [x[0] for x in r] == ["Perro", "Gato"]
    engine.dispose()
    engine3.dispose()
