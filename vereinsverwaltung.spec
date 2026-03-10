# -*- mode: python ; coding: utf-8 -*-
# vereinsverwaltung.spec
#
# Aufruf:  pyinstaller vereinsverwaltung.spec
#
# Ergebnis: dist\Vereinsverwaltung.exe  (Single-File)

import sys
from pathlib import Path

ROOT = Path(SPECPATH)   # Verzeichnis dieser .spec-Datei

block_cipher = None

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # App-Quellcode ins Bundle
        (str(ROOT / "app"),          "app"),
        # GUI-Dateien
        (str(ROOT / "gui" / "vereinsverwaltung.html"), "gui"),
        (str(ROOT / "gui" / "vereinsverwaltung.css"),  "gui"),
        (str(ROOT / "gui" / "vereinsverwaltung.js"),   "gui"),
        # .env-Vorlage (wird beim ersten Start als .env kopiert)
        (str(ROOT / ".env.example"), "."),
    ],
    hiddenimports=[
        # FastAPI / Starlette Internals
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.responses",
        "starlette.staticfiles",
        "starlette.testclient",
        # Uvicorn
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # Pydantic
        "pydantic.v1",
        "pydantic_core",
        # SQLAlchemy dialects
        "sqlalchemy.dialects.sqlite",
        # Email-Validierung (Pydantic optional dep)
        "email_validator",
        # Dotenv
        "dotenv",
        # App-eigene Module
        "app.main",
        "app.database",
        "app.ftp_sync",
        "app.models.member",
        "app.models.konto",
        "app.models.buchung",
        "app.routers.members",
        "app.routers.konten",
        "app.routers.buchungen",
        "app.schemas.member",
        "app.schemas.konto",
        "app.schemas.buchung",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "httpx",
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Vereinsverwaltung",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # UPX-Komprimierung (kleiner, braucht upx.exe im PATH)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # Konsolenfenster zeigt Fehler beim Start
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="icon.ico",  # optional: Pfad zu einer .ico-Datei
)
