import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError


def _ejecutar_migracion(
    backend_dir: Path,
    db_path: Path,
    accion: str,
    objetivo: str,
) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", accion, objetivo],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_migracion_cobros_aplica_integridad_y_es_reversible(tmp_path: Path) -> None:
    db_path = tmp_path / "cobros.db"
    backend_dir = Path(__file__).resolve().parents[2]
    _ejecutar_migracion(backend_dir, db_path, "upgrade", "head")

    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _habilitar_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    inspector = inspect(engine)
    esperadas = {
        "cargo": {
            (("persona_id",), "persona", ("id",)),
            (("paciente_id",), "paciente", ("id",)),
            (("creado_por",), "usuario", ("id",)),
        },
        "ajuste_precio": {
            (("usuario_id",), "usuario", ("id",)),
        },
        "pago": {
            (("usuario_id",), "usuario", ("id",)),
            (("empleado_id",), "empleado", ("persona_id",)),
            (("pago_revertido_id", "cargo_id"), "pago", ("id", "cargo_id")),
        },
        "servicio_prestado": {
            (("empleado_id",), "empleado", ("persona_id",)),
        },
        "gasto_externo": {
            (("empleado_id",), "empleado", ("persona_id",)),
            (("registrado_por",), "usuario", ("id",)),
        },
    }
    for tabla, fks_esperadas in esperadas.items():
        fks = {
            (
                tuple(fk["constrained_columns"]),
                fk["referred_table"],
                tuple(fk["referred_columns"]),
            )
            for fk in inspector.get_foreign_keys(tabla)
        }
        assert fks_esperadas <= fks

    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM medio_pago")
        ).scalar_one() == 4
        usuario_id = connection.execute(
            text(
                "INSERT INTO usuario (username, password_hash, rol) "
                "VALUES ('duenio-test', 'hash', 'DUENIO')"
            )
        ).lastrowid
        persona_id = connection.execute(
            text("INSERT INTO persona (nombre, apellido) VALUES ('Ana', 'Prueba')")
        ).lastrowid
        paciente_id = connection.execute(
            text(
                "INSERT INTO paciente (nombre, especie_id) "
                "VALUES ('Firulais', (SELECT id FROM especie WHERE nombre = 'Perro'))"
            )
        ).lastrowid
        empleado_persona_id = connection.execute(
            text(
                "INSERT INTO persona (nombre, apellido) "
                "VALUES ('Veterinario', 'Externo')"
            )
        ).lastrowid
        connection.execute(
            text(
                "INSERT INTO empleado (persona_id, tipo) "
                "VALUES (:persona_id, 'EXTERNO')"
            ),
            {"persona_id": empleado_persona_id},
        )
        cargo_ids = [
            connection.execute(
                text(
                    "INSERT INTO cargo "
                    "(persona_id, paciente_id, concepto, total_inicial, creado_por) "
                    "VALUES (:persona_id, :paciente_id, 'consulta', 1000, :usuario_id)"
                ),
                {
                    "persona_id": persona_id,
                    "paciente_id": paciente_id,
                    "usuario_id": usuario_id,
                },
            ).lastrowid
            for _ in range(2)
        ]
        pago_id = connection.execute(
            text(
                "INSERT INTO pago "
                "(cargo_id, monto, tipo, medio_pago_id, fecha, usuario_id) "
                "VALUES (:cargo_id, 500, 'PAGO', "
                "(SELECT id FROM medio_pago WHERE codigo = 'EFECTIVO'), "
                "'2026-01-01', :usuario_id)"
            ),
            {"cargo_id": cargo_ids[0], "usuario_id": usuario_id},
        ).lastrowid
        ajuste_id = connection.execute(
            text(
                "INSERT INTO ajuste_precio "
                "(cargo_id, precio_anterior, precio_nuevo, motivo, usuario_id) "
                "VALUES (:cargo_id, 1000, 900, 'ajuste', :usuario_id)"
            ),
            {"cargo_id": cargo_ids[0], "usuario_id": usuario_id},
        ).lastrowid

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO pago "
                    "(cargo_id, monto, tipo, pago_revertido_id, medio_pago_id, fecha, usuario_id) "
                    "VALUES (:cargo_id, 500, 'REVERSO', :pago_id, "
                    "(SELECT id FROM medio_pago WHERE codigo = 'EFECTIVO'), "
                    "'2026-01-02', :usuario_id)"
                ),
                {
                    "cargo_id": cargo_ids[1],
                    "pago_id": pago_id,
                    "usuario_id": usuario_id,
                },
            )

    inserciones_con_importes_decimales = [
        (
            "INSERT INTO cargo "
            "(persona_id, concepto, total_inicial, creado_por) "
            "VALUES (:persona_id, 'consulta', 1.5, :usuario_id)",
            {"persona_id": persona_id, "usuario_id": usuario_id},
        ),
        (
            "INSERT INTO ajuste_precio "
            "(cargo_id, precio_anterior, precio_nuevo, motivo, usuario_id) "
            "VALUES (:cargo_id, 1000, 1.5, 'ajuste', :usuario_id)",
            {"cargo_id": cargo_ids[0], "usuario_id": usuario_id},
        ),
        (
            "INSERT INTO ajuste_precio "
            "(cargo_id, precio_anterior, precio_nuevo, motivo, usuario_id) "
            "VALUES (:cargo_id, 1.5, 1000, 'ajuste', :usuario_id)",
            {"cargo_id": cargo_ids[0], "usuario_id": usuario_id},
        ),
        (
            "INSERT INTO pago "
            "(cargo_id, monto, tipo, medio_pago_id, fecha, usuario_id) "
            "VALUES (:cargo_id, 1.5, 'PAGO', "
            "(SELECT id FROM medio_pago WHERE codigo = 'EFECTIVO'), "
            "'2026-01-03', :usuario_id)",
            {"cargo_id": cargo_ids[0], "usuario_id": usuario_id},
        ),
        (
            "INSERT INTO gasto_externo "
            "(empleado_id, descripcion, monto, fecha, registrado_por) "
            "VALUES (:empleado_id, 'cirugia', 1.5, '2026-01-03', :usuario_id)",
            {"empleado_id": empleado_persona_id, "usuario_id": usuario_id},
        ),
    ]
    for consulta, parametros in inserciones_con_importes_decimales:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(consulta), parametros)

    mutaciones_inmutables = [
        ("UPDATE cargo SET concepto = 'corregido' WHERE id = :id", cargo_ids[0]),
        ("DELETE FROM cargo WHERE id = :id", cargo_ids[0]),
        ("UPDATE ajuste_precio SET motivo = 'corregido' WHERE id = :id", ajuste_id),
        ("DELETE FROM ajuste_precio WHERE id = :id", ajuste_id),
        ("UPDATE pago SET monto = 600 WHERE id = :id", pago_id),
        ("DELETE FROM pago WHERE id = :id", pago_id),
    ]
    for consulta, registro_id in mutaciones_inmutables:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(consulta), {"id": registro_id})

    with engine.begin() as connection:
        triggers = {
            fila[0]
            for fila in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            )
        }
    assert {
        "trg_cargo_no_update",
        "trg_cargo_no_delete",
        "trg_ajuste_precio_no_update",
        "trg_ajuste_precio_no_delete",
        "trg_pago_no_update",
        "trg_pago_no_delete",
    } <= triggers

    engine.dispose()
    _ejecutar_migracion(backend_dir, db_path, "downgrade", "base")
