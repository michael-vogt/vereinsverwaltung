from contextlib import asynccontextmanager
import logging
from pathlib import Path

# .env laden – muss vor allen anderen Importen geschehen, die os.getenv() nutzen
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")  # Projekt-Root/.env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, load_from_bytes
from app.ftp_sync import load_db, start_auto_sync, stop_auto_sync, sync_now, sync_status
from app.routers import members, konten, buchungen

# Modelle registrieren
import app.models.member   # noqa: F401
import app.models.konto    # noqa: F401
import app.models.buchung  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Vereinsverwaltung API läuft"}


@app.get("/sync/status", tags=["Sync"])
def get_sync_status():
    """Zeigt wann zuletzt synchronisiert wurde und ob Fehler aufgetreten sind."""
    return sync_status()


@app.post("/sync/now", tags=["Sync"])
def trigger_sync():
    """Löst sofort einen manuellen Sync aus."""
    return sync_now(engine)


