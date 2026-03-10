"""
database.py
-----------
Lädt die SQLite-DB beim Start in den Speicher (via FTP oder leer).
Alle Operationen laufen gegen die In-Memory-Instanz.
"""

import sqlite3
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# ── Persistente In-Memory-Connection ──────────────────────────────────────────
# Eine einzelne sqlite3-Connection wird als Singleton gehalten.
# StaticPool gibt SQLAlchemy immer dieselbe Connection zurück, sodass
# In-Memory-Daten nicht verloren gehen.
_sqlite_conn = sqlite3.connect(":memory:", check_same_thread=False)


def _get_conn():
    return _sqlite_conn


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    creator=_get_conn,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def load_from_bytes(db_bytes: bytes) -> None:
    """
    Füllt die In-Memory-DB aus einem SQLite-Byte-Dump.
    Schreibt direkt in _sqlite_conn, die SQLAlchemy via creator= immer
    wiederverwendet – so gehen keine Daten durch Pool-Mechanismen verloren.
    """
    if not db_bytes:
        return

    src = sqlite3.connect(":memory:")
    src.deserialize(db_bytes)
    src.backup(_sqlite_conn)
    src.close()

    logger.info("In-Memory-DB aus %d Bytes wiederhergestellt.", len(db_bytes))


def get_db():
    """FastAPI-Dependency: liefert eine DB-Session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
