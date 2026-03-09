"""
database.py
-----------
Lädt die SQLite-DB beim Start in den Speicher (via FTP oder leer).
Alle Operationen laufen gegen die In-Memory-Instanz.
"""

import io
import sqlite3
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# ── In-Memory Engine ───────────────────────────────────────────────────────
# StaticPool sorgt dafür, dass SQLAlchemy immer dieselbe In-Memory-Verbindung
# nutzt – SQLite-In-Memory-DBs sind sonst connection-gebunden.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def load_from_bytes(db_bytes: bytes) -> None:
    """
    Füllt die In-Memory-DB aus einem SQLite-Byte-Dump.
    Wird beim Start aufgerufen, wenn eine DB vom FTP geladen wurde.
    """
    if not db_bytes:
        return

    # Bytes in eine temporäre SQLite-Connection laden
    src = sqlite3.connect(":memory:")
    src.deserialize(db_bytes)

    # Inhalte in die Engine-Verbindung kopieren
    raw = engine.raw_connection()
    try:
        inner = getattr(raw, "dbapi_connection", raw)
        src.backup(inner)
    finally:
        raw.close()
        src.close()

    logger.info("In-Memory-DB aus %d Bytes wiederhergestellt.", len(db_bytes))


def get_db():
    """FastAPI-Dependency: liefert eine DB-Session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
