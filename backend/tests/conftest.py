import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.base import Base
from app.core.config import get_settings
from app.core.db import get_db
from app.main import app


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> str:
    db_file = tmp_path / "test.db"
    return f"sqlite:///{db_file}"


@pytest.fixture
def engine_sqlite(tmp_db_path: str):
    engine = create_engine(tmp_db_path, connect_args={"check_same_thread": False}, future=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(engine_sqlite) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_sqlite, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def sembrar_config(db_session: Session):
    from app.core import parametros

    parametros._limpiar_cache()

    def _sembrar(clave: str, valor, tipo: str, modulo: str | None = None, descripcion: str | None = None):
        return parametros.registrar_parametro(
            db_session, clave, valor, tipo, modulo=modulo, descripcion=descripcion
        )

    return _sembrar
