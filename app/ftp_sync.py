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
# WICHTIG: os.getenv() wird lazy in den Funktionen gelesen, nicht auf
# Modulebene. So ist sichergestellt, dass load_dotenv() in main.py bereits
# ausgeführt wurde bevor die Werte gelesen werden.

def _cfg_db_source()     -> str:   return os.getenv("DB_SOURCE", "").lower()
def _cfg_local_path()    -> str:   return os.getenv("LOCAL_DB_PATH", "data.db")
def _cfg_ftp_host()      -> str:   return os.getenv("FTP_HOST", "")
def _cfg_ftp_user()      -> str:   return os.getenv("FTP_USER", "")
def _cfg_ftp_password()  -> str:   return os.getenv("FTP_PASSWORD", "")
def _cfg_ftp_path()      -> str:   return os.getenv("FTP_PATH", "/data.db")
def _cfg_ftp_tls()       -> bool:  return os.getenv("FTP_USE_TLS", "false").lower() == "true"
def _cfg_sync_interval() -> int:   return int(os.getenv("SYNC_INTERVAL", "300"))

# ── Interner Zustand ───────────────────────────────────────────────────────
_last_sync: datetime | None = None
_sync_error: str | None = None
_sync_lock  = threading.Lock()
_sync_timer: threading.Timer | None = None


# ══════════════════════════════════════════════════════════════════════════
# Backend: Lokal
# ══════════════════════════════════════════════════════════════════════════

def _load_local() -> bytes | None:
    path = Path(_cfg_local_path())
    if not path.exists():
        logger.info("Lokale DB '%s' nicht gefunden – starte frisch.", path)
        return None
    data = path.read_bytes()
    logger.info("Lokale DB geladen: %s (%d Bytes)", path.resolve(), len(data))
    return data


def _save_local(db_bytes: bytes) -> None:
    path = Path(_cfg_local_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".db.tmp")
    tmp.write_bytes(db_bytes)
    tmp.replace(path)
    logger.info("Lokale DB gespeichert: %s (%d Bytes)", path.resolve(), len(db_bytes))


# ══════════════════════════════════════════════════════════════════════════
# Backend: FTP
# ══════════════════════════════════════════════════════════════════════════

def _ftp_connect() -> ftplib.FTP:
    if _cfg_ftp_tls():
        ftp = ftplib.FTP_TLS()
        ftp.connect(_cfg_ftp_host(), 21)
        ftp.auth()
        ftp.login(_cfg_ftp_user(), _cfg_ftp_password())
        ftp.prot_p()
    else:
        ftp = ftplib.FTP()
        ftp.connect(_cfg_ftp_host(), 21)
        ftp.login(_cfg_ftp_user(), _cfg_ftp_password())
    ftp.set_pasv(True)
    return ftp


def _load_ftp() -> bytes | None:
    if not _cfg_ftp_host():
        raise ValueError("FTP_HOST nicht konfiguriert.")
    ftp = _ftp_connect()
    buf = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {_cfg_ftp_path()}", buf.write)
        logger.info("DB vom FTP geladen: %s (%d Bytes)", _cfg_ftp_path(), buf.tell())
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
        directory = "/".join(_cfg_ftp_path().split("/")[:-1])
        if directory:
            parts = directory.strip("/").split("/")
            current = ""
            for part in parts:
                current += f"/{part}"
                try:
                    ftp.mkd(current)
                except ftplib.error_perm:
                    pass
        ftp.storbinary(f"STOR {_cfg_ftp_path()}", io.BytesIO(db_bytes))
        logger.info("DB auf FTP gespeichert: %s (%d Bytes)", _cfg_ftp_path(), len(db_bytes))
    finally:
        ftp.quit()


# ══════════════════════════════════════════════════════════════════════════
# Dispatcher – wählt das richtige Backend
# ══════════════════════════════════════════════════════════════════════════

def _active_backend() -> str:
    if _cfg_db_source() == "local":
        return "local"
    if _cfg_db_source() == "ftp" or _cfg_ftp_host():
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

# ══════════════════════════════════════════════════════════════════════════
# Engine-Serialisierung
# ══════════════════════════════════════════════════════════════════════════

def get_db_bytes_from_engine(engine) -> bytes:
    """
    Serialisiert die In-Memory-SQLite zu Bytes.
    Liest direkt aus _sqlite_conn statt über engine.raw_connection(),
    um Pool-seitiges rollback() beim close() zu vermeiden.
    """
    from app.database import _sqlite_conn
    tmp = sqlite3.connect(":memory:")
    _sqlite_conn.backup(tmp)
    db_bytes = tmp.serialize()
    tmp.close()
    return db_bytes


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
        _sync_timer = threading.Timer(_cfg_sync_interval(), _tick)
        _sync_timer.daemon = True
        _sync_timer.start()

    _sync_timer = threading.Timer(_cfg_sync_interval(), _tick)
    _sync_timer.daemon = True
    _sync_timer.start()
    logger.info("Auto-Sync gestartet (Backend: %s, Intervall: %ds)", _active_backend(), _cfg_sync_interval())


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
        "interval_seconds": _cfg_sync_interval(),
    }
    if backend == "local":
        info["local_path"] = str(Path(_cfg_local_path()).resolve())
    elif backend == "ftp":
        info["ftp_host"] = _cfg_ftp_host()
        info["ftp_path"] = _cfg_ftp_path()
    return info
