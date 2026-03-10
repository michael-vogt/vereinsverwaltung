"""
Vereinsverwaltung – Launcher
Startet die FastAPI-API im Hintergrund und öffnet die GUI im Browser.
"""
import os
import sys
import time
import shutil
import socket
import threading
import webbrowser
from pathlib import Path


# ── Pfad-Helfer ──────────────────────────────────────────────────────────────

def _base_dir() -> Path:
    """Verzeichnis der .exe (oder des Skripts im Entwicklungsmodus)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _bundle_dir() -> Path:
    """PyInstaller _MEIPASS-Verzeichnis, oder Skript-Verzeichnis."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)   # type: ignore[attr-defined]
    return Path(__file__).parent


# ── Fehler-Dialog ────────────────────────────────────────────────────────────

def _error_dialog(title: str, message: str):
    """Zeigt einen Windows-Fehlerdialog; fällt auf print() zurück."""
    print(f"FEHLER: {title}\n{message}", file=sys.stderr)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass


# ── .env laden ───────────────────────────────────────────────────────────────

def _load_env():
    env_path = _base_dir() / ".env"
    if not env_path.exists():
        example = _bundle_dir() / ".env.example"
        if example.exists():
            shutil.copy(example, env_path)
    from dotenv import load_dotenv
    load_dotenv(env_path)


# ── Freien Port finden ───────────────────────────────────────────────────────

def _free_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Kein freier Port gefunden (8765-8814)")


# ── Warten bis API antwortet ─────────────────────────────────────────────────

def _wait_for_api(port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


# ── API-Server starten ───────────────────────────────────────────────────────

def _start_api(port: int, error_holder: list):
    """Laeuft im Hintergrund-Thread. Schreibt Fehler in error_holder[0]."""
    try:
        bundle = str(_bundle_dir())
        if bundle not in sys.path:
            sys.path.insert(0, bundle)

        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            log_level="info",
        )
    except Exception as exc:
        error_holder.append(str(exc))


# ── Tray-Icon ────────────────────────────────────────────────────────────────

def _run_tray(port: int):
    """System-Tray-Icon; faellt zurueck auf blockierenden Wait."""
    try:
        from PIL import Image, ImageDraw
        import pystray

        def _icon_image():
            img = Image.new("RGB", (64, 64), color=(30, 30, 40))
            d = ImageDraw.Draw(img)
            d.ellipse([8, 8, 56, 56], fill=(74, 158, 255))
            d.text((22, 20), "V", fill="white")
            return img

        def on_open(icon, item):
            webbrowser.open(f"http://127.0.0.1:{port}/")

        def on_quit(icon, item):
            icon.stop()
            os._exit(0)

        icon = pystray.Icon(
            "Vereinsverwaltung",
            _icon_image(),
            "Vereinsverwaltung",
            menu=pystray.Menu(
                pystray.MenuItem("Oeffnen", on_open),
                pystray.MenuItem("Beenden", on_quit),
            ),
        )
        icon.run()
    except Exception:
        threading.Event().wait()


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    try:
        _load_env()
        port = _free_port(8765)
    except Exception as exc:
        _error_dialog("Vereinsverwaltung - Startfehler", str(exc))
        sys.exit(1)

    error_holder: list = []
    api_thread = threading.Thread(
        target=_start_api, args=(port, error_holder), daemon=True
    )
    api_thread.start()

    if not _wait_for_api(port, timeout=20.0):
        err = error_holder[0] if error_holder else "Timeout nach 20 Sekunden."
        _error_dialog(
            "Vereinsverwaltung - API nicht erreichbar",
            f"Die API konnte auf Port {port} nicht gestartet werden.\n\n{err}"
        )
        sys.exit(1)

    webbrowser.open(f"http://127.0.0.1:{port}/")
    _run_tray(port)


if __name__ == "__main__":
    main()
