from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(
    dbapi_connection: DBAPIConnection, connection_record: ConnectionPoolEntry
) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaccion_inmediata(db: Session) -> Iterator[None]:
    """Serializa una escritura SQLite y confirma o revierte la unidad completa."""
    if db.get_bind().dialect.name != "sqlite":
        raise RuntimeError("La transacción inmediata requiere SQLite")

    try:
        db.execute(text("BEGIN IMMEDIATE"))
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
