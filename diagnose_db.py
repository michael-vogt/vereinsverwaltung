"""
diagnose_db.py
--------------
Liest die .env und inspiziert die DB-Datei direkt (lokal oder FTP).
Zeigt Tabellen, Zeilenzahlen und die ersten 3 Datensätze je Tabelle.

Ausführen:
    python diagnose_db.py
"""

import io
import os
import sqlite3
import sys
from pathlib import Path

# .env laden
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / "api_project" / ".env")
    load_dotenv(Path(__file__).parent / ".env")  # falls direkt im Projektverzeichnis
except ImportError:
    print("Hinweis: python-dotenv nicht installiert – lese .env manuell")
    env_candidates = [
        Path(__file__).parent / "api_project" / ".env",
        Path(__file__).parent / ".env",
    ]
    for env_file in env_candidates:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            print(f".env geladen aus: {env_file}")
            break

DB_SOURCE     = os.getenv("DB_SOURCE", "").lower()
LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "data.db")
FTP_HOST      = os.getenv("FTP_HOST", "")
FTP_USER      = os.getenv("FTP_USER", "")
FTP_PASSWORD  = os.getenv("FTP_PASSWORD", "")
FTP_PATH      = os.getenv("FTP_PATH", "/data.db")
FTP_USE_TLS   = os.getenv("FTP_USE_TLS", "false").lower() == "true"

print(f"\n{'='*60}")
print(f"  DB-Diagnose")
print(f"{'='*60}")
print(f"  DB_SOURCE : {DB_SOURCE or '(nicht gesetzt)'}")


# ── DB-Bytes laden ─────────────────────────────────────────────────────────

def load_local() -> bytes | None:
    path = Path(LOCAL_DB_PATH)
    print(f"  Pfad      : {path.resolve()}")
    if not path.exists():
        print("  ✗ Datei nicht gefunden!")
        return None
    data = path.read_bytes()
    print(f"  Größe     : {len(data):,} Bytes")
    return data


def load_ftp() -> bytes | None:
    import ftplib
    print(f"  FTP-Host  : {FTP_HOST}")
    print(f"  FTP-Pfad  : {FTP_PATH}")
    print(f"  TLS       : {FTP_USE_TLS}")
    try:
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
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {FTP_PATH}", buf.write)
        ftp.quit()
        data = buf.getvalue()
        print(f"  Größe     : {len(data):,} Bytes")
        return data
    except Exception as e:
        print(f"  ✗ FTP-Fehler: {e}")
        return None


if DB_SOURCE == "local":
    db_bytes = load_local()
elif DB_SOURCE == "ftp" or FTP_HOST:
    db_bytes = load_ftp()
else:
    print("  ✗ Keine Datenquelle konfiguriert (DB_SOURCE=local|ftp)")
    sys.exit(1)

if not db_bytes:
    print("\n  Keine DB-Daten gefunden – nichts zu analysieren.")
    sys.exit(0)


# ── SQLite-Analyse ─────────────────────────────────────────────────────────

print(f"\n{'─'*60}")
print("  Tabellenstruktur")
print(f"{'─'*60}")

conn = sqlite3.connect(":memory:")
conn.deserialize(db_bytes)

tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

if not tables:
    print("  ✗ Keine Tabellen gefunden! Die DB ist leer oder beschädigt.")
    sys.exit(0)

for (tbl,) in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM \"{tbl}\"").fetchone()[0]
    print(f"\n  [{tbl}]  {count} Zeilen")

    # Spalten
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info(\"{tbl}\")").fetchall()]
    print(f"  Spalten: {', '.join(cols)}")

    # Erste 3 Zeilen
    rows = conn.execute(f"SELECT * FROM \"{tbl}\" LIMIT 3").fetchall()
    for row in rows:
        print(f"    → {row}")
    if count > 3:
        print(f"    ... ({count - 3} weitere)")

conn.close()
print(f"\n{'='*60}\n")