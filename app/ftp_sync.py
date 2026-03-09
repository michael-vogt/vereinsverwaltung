"""
db_sync.py  (ehemals ftp_sync.py)
----------------------------------
Austauschbare Datenquellen für die In-Memory-SQLite-DB.

Konfiguration über .env – genau EINE Quelle angeben:

  Lokale Datei:
      DB_SOURCE=local
      LOCAL_DB_PATH=/pfad/zur/data.db        # absolut oder relativ

  FTP / FTPS:
      DB_SOURCE=ftp
      FTP_HOST=ftp.meinverein.de
      FTP_USER=benutzer
      FTP_PASSWORD=passwort
      FTP_PATH=/vereinsverwaltung/data.db
      FTP_USE_TLS=false                      # true für FTPS

  Gemeinsame Optionen:
      SYNC_INTERVAL=300                      # Sekunden zwischen Auto-Syncs
"""

from __future__ import annotations

import io
import os
import sqlite3
import logging
import threading
import ftplib
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Konfiguration ──────────────────────────────────────────────────────────
DB_SOURCE     = os.getenv("DB_SOURCE", "").lower()          # "local" | "ftp"
LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "data.db")
FTP_HOST      = os.getenv("FTP_HOST", "")
FTP_USER      = os.getenv("FTP_USER", "")
FTP_PASSWORD  = os.getenv("FTP_PASSWORD", "")
FTP_PATH      = os.getenv("FTP_PATH", "/data.db")
FTP_USE_TLS   = os.getenv("FTP_USE_TLS", "false").lower() == "true"
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "300"))

# ── Interner Zustand ───────────────────────────────────────────────────────
_last_sync: datetime | None = None
_sync_error: str | None = None
_sync_lock  = threading.Lock()
_sync_timer: threading.Timer | None = None


# ══════════════════════════════════════════════════════════════════════════
# Backend: Lokal
# ══════════════════════════════════════════════════════════════════════════

def _load_local() -> bytes | None:
    path = Path(LOCAL_DB_PATH)
    if not path.exists():
        logger.info("Lokale DB '%s' nicht gefunden – starte frisch.", path)
        return None
    data = path.read_bytes()
    logger.info("Lokale DB geladen: %s (%d Bytes)", path.resolve(), len(data))
    return data


def _save_local(db_bytes: bytes) -> None:
    path = Path(LOCAL_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomares Schreiben: zuerst in .tmp, dann umbenennen
    tmp = path.with_suffix(".db.tmp")
    tmp.write_bytes(db_bytes)
    tmp.replace(path)
    logger.info("Lokale DB gespeichert: %s (%d Bytes)", path.resolve(), len(db_bytes))


# ══════════════════════════════════════════════════════════════════════════
# Backend: FTP
# ══════════════════════════════════════════════════════════════════════════

def _ftp_connect() -> ftplib.FTP:
    if FTP_USE_TLS:
        ftp = ftplib.FTP_TLS()
        ftp.connect(FTP_HOST, 21)
        ftp.auth()
        ftp.login(FTP_USER, FTP_PASSWORD)
        ftp.prot_p()
    else:
        ftp = ftplib.FTP()
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
    ftp.set_pasv(True)
    return ftp


def _load_ftp() -> bytes | None:
    if not FTP_HOST:
        raise ValueError("FTP_HOST nicht konfiguriert.")
    ftp = _ftp_connect()
    buf = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {FTP_PATH}", buf.write)
        logger.info("DB vom FTP geladen: %s (%d Bytes)", FTP_PATH, buf.tell())
        return buf.getvalue()
    except ftplib.error_perm as e:
        if "550" in str(e):
            logger.info("Keine DB auf FTP gefunden – starte frisch.")
            return None
        raise
    finally:
        ftp.quit()


def _save_ftp(db_bytes: bytes) -> None:
    ftp = _ftp_connect()
    try:
        directory = "/".join(FTP_PATH.split("/")[:-1])
        if directory:
            parts = directory.strip("/").split("/")
            current = ""
            for part in parts:
                current += f"/{part}"
                try:
                    ftp.mkd(current)
                except ftplib.error_perm:
                    pass  # Existiert bereits
        ftp.storbinary(f"STOR {FTP_PATH}", io.BytesIO(db_bytes))
        logger.info("DB auf FTP gespeichert: %s (%d Bytes)", FTP_PATH, len(db_bytes))
    finally:
        ftp.quit()


# ══════════════════════════════════════════════════════════════════════════
# Dispatcher – wählt das richtige Backend
# ══════════════════════════════════════════════════════════════════════════

def _active_backend() -> str:
    """Gibt das konfigurierte Backend zurück ('local', 'ftp' oder 'none')."""
    if DB_SOURCE == "local":
        return "local"
    if DB_SOURCE == "ftp" or FTP_HOST:   # Rückwärtskompatibilität: FTP_HOST gesetzt → ftp
        return "ftp"
    return "none"


def load_db() -> bytes | None:
    """Lädt die DB aus der konfigurierten Quelle."""
    backend = _active_backend()
    if backend == "local":
        return _load_local()
    if backend == "ftp":
        return _load_ftp()
    logger.warning("Keine Datenquelle konfiguriert (DB_SOURCE=local|ftp). Starte leer.")
    return None


def _save_db(db_bytes: bytes) -> None:
    """Schreibt die DB in die konfigurierte Quelle."""
    backend = _active_backend()
    if backend == "local":
        _save_local(db_bytes)
    elif backend == "ftp":
        _save_ftp(db_bytes)
    else:
        logger.warning("Kein Sync-Ziel konfiguriert – Daten nur im RAM.")


# ══════════════════════════════════════════════════════════════════════════
# Engine-Serialisierung
# ══════════════════════════════════════════════════════════════════════════

def get_db_bytes_from_engine(engine) -> bytes:
    """Serialisiert die In-Memory-SQLite zu Bytes."""
    raw_conn = engine.raw_connection()
    try:
        file_conn = sqlite3.connect(":memory:")
        inner = getattr(raw_conn, "dbapi_connection", raw_conn)
        inner.backup(file_conn)
        db_bytes = file_conn.serialize()
        file_conn.close()
        return db_bytes
    finally:
        raw_conn.close()


# ══════════════════════════════════════════════════════════════════════════
# Sync-Steuerung (öffentliche API)
# ══════════════════════════════════════════════════════════════════════════

def sync_now(engine) -> dict:
    """Führt einen sofortigen Sync durch. Gibt Status-Dict zurück."""
    global _last_sync, _sync_error
    with _sync_lock:
        try:
            db_bytes = get_db_bytes_from_engine(engine)
            _save_db(db_bytes)
            _last_sync = datetime.now()
            _sync_error = None
            return {"ok": True, "timestamp": _last_sync.isoformat(), "bytes": len(db_bytes)}
        except Exception as e:
            _sync_error = str(e)
            logger.error("Sync fehlgeschlagen: %s", e)
            return {"ok": False, "timestamp": None, "error": str(e)}


def start_auto_sync(engine) -> None:
    """Startet den Hintergrund-Sync-Timer."""
    global _sync_timer

    def _tick():
        global _sync_timer
        sync_now(engine)
        _sync_timer = threading.Timer(SYNC_INTERVAL, _tick)
        _sync_timer.daemon = True
        _sync_timer.start()

    _sync_timer = threading.Timer(SYNC_INTERVAL, _tick)
    _sync_timer.daemon = True
    _sync_timer.start()
    logger.info("Auto-Sync gestartet (Backend: %s, Intervall: %ds)", _active_backend(), SYNC_INTERVAL)


def stop_auto_sync() -> None:
    """Stoppt den Sync-Timer."""
    global _sync_timer
    if _sync_timer:
        _sync_timer.cancel()
        _sync_timer = None


def sync_status() -> dict:
    """Gibt den aktuellen Sync-Status zurück."""
    backend = _active_backend()
    info: dict = {
        "backend": backend,
        "last_sync": _last_sync.isoformat() if _last_sync else None,
        "error": _sync_error,
        "interval_seconds": SYNC_INTERVAL,
    }
    if backend == "local":
        info["local_path"] = str(Path(LOCAL_DB_PATH).resolve())
    elif backend == "ftp":
        info["ftp_host"] = FTP_HOST
        info["ftp_path"] = FTP_PATH
    return info
