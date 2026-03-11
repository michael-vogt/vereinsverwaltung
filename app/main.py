from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# .env laden – muss vor allen anderen Importen geschehen, die os.getenv() nutzen
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")  # Projekt-Root/.env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine, Base, load_from_bytes
from app.ftp_sync import load_db, start_auto_sync, stop_auto_sync, sync_now, sync_status
from app.routers import members, konten, buchungen

# Modelle registrieren
import app.models.member   # noqa: F401
import app.models.konto    # noqa: F401
import app.models.buchung  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _gui_dir() -> Path:
    """
    Sucht die GUI-Dateien:
    1. Im PyInstaller-Bundle unter 'gui/'
    2. Im Entwicklungsmodus: <project-root>/gui/
    3. Direkt im Projekt-Root (Fallback)
    """
    if getattr(sys, "frozen", False):
        bundle = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return bundle / "gui"
    root = Path(__file__).parent.parent
    if (root / "gui").exists():
        return root / "gui"
    return root


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    # Tabellen-Schema sicherstellen BEVOR Daten geladen werden.
    # create_all() auf einer leeren DB ist harmlos; auf einer bereits
    # befüllten DB würde es Daten überschreiben wenn es danach käme.
    Base.metadata.create_all(bind=engine)

    logger.info("Lade Datenbank...")
    try:
        db_bytes = load_db()
        if db_bytes:
            load_from_bytes(db_bytes)
            logger.info("Datenbank erfolgreich geladen.")
        else:
            logger.info("Keine bestehende DB gefunden – starte mit leerer DB.")
    except Exception as e:
        logger.error("Laden fehlgeschlagen: %s – starte mit leerer DB.", e)

    # Auto-Sync starten
    start_auto_sync(engine)

    yield  # App läuft

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("Shutdown: finaler Sync...")
    stop_auto_sync()
    sync_now(engine)
    logger.info("Shutdown abgeschlossen.")


app = FastAPI(
    title="Vereinsverwaltung API",
    description="REST API zur Verwaltung von Vereinsmitgliedern und Buchführung",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(members.router,   prefix="/members",   tags=["Mitglieder"])
app.include_router(konten.router,    prefix="/konten",    tags=["Kontenrahmen"])
app.include_router(buchungen.router, prefix="/buchungen", tags=["Buchungen"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.get("/sync/status", tags=["Sync"])
def get_sync_status():
    """Zeigt wann zuletzt synchronisiert wurde und ob Fehler aufgetreten sind."""
    return sync_status()


@app.post("/sync/now", tags=["Sync"])
def trigger_sync():
    """Löst sofort einen manuellen Sync aus."""
    return sync_now(engine)


# ── Statische GUI-Dateien – MUSS als letztes gemountet werden! ────────────────
# app.mount("/") fängt ALLE nicht gematchten Pfade ab.
# Deshalb müssen alle API-Routen davor registriert sein.
@app.get("/", tags=["GUI"], include_in_schema=False)
def gui_index():
    """Liefert die GUI-Startseite aus."""
    gui = _gui_dir()
    index = gui / "vereinsverwaltung.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    return {"status": "ok", "message": "Vereinsverwaltung API läuft – GUI nicht gefunden"}


_gui_path = _gui_dir()
if _gui_path.exists():
    app.mount("/", StaticFiles(directory=str(_gui_path)), name="gui")


