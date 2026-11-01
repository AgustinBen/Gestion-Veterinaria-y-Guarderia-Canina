import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.db import transaccion_inmediata


def test_transaccion_inmediata_confirma_y_revierte(db_session):
    db_session.execute(text("CREATE TABLE transaccion_test (valor INTEGER NOT NULL)"))
    db_session.commit()

    with transaccion_inmediata(db_session):
        db_session.execute(text("INSERT INTO transaccion_test (valor) VALUES (1)"))

    assert db_session.execute(
        text("SELECT valor FROM transaccion_test")
    ).scalar_one() == 1

    with pytest.raises(RuntimeError, match="forzar rollback"):
        with transaccion_inmediata(db_session):
            db_session.execute(text("INSERT INTO transaccion_test (valor) VALUES (2)"))
            raise RuntimeError("forzar rollback")

    assert db_session.execute(
        text("SELECT valor FROM transaccion_test ORDER BY valor")
    ).scalars().all() == [1]


def test_pragmas_y_foreign_key_en_conexion(client):
    # usar una conexión del engine de la app? pero en tests usamos fixture client con db_session override
    # el ticket dice: "al abrir una conexión, PRAGMA foreign_keys devuelve 1 y journal_mode es wal"
    from app.core.db import engine

    with engine.connect() as conn:
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        jm = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert fk == 1
        assert str(jm).lower() == "wal"


def test_insertar_fk_inexistente_falla(db_session):
    # crear tabla con FK
    db_session.execute(text("CREATE TABLE padre (id INTEGER PRIMARY KEY)"))
    db_session.execute(
        text(
            "CREATE TABLE hijo ("
            "id INTEGER PRIMARY KEY, "
            "padre_id INTEGER NOT NULL, "
            "FOREIGN KEY(padre_id) REFERENCES padre(id))"
        )
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(text("INSERT INTO hijo (id, padre_id) VALUES (1, 999)"))
        db_session.commit()

    db_session.rollback()
