@echo off
:: build.bat – Vereinsverwaltung.exe erstellen
:: Voraussetzungen: Python 3.11+, pip
:: Aufruf: build.bat

setlocal

echo ============================================
echo  Vereinsverwaltung – Windows Build
echo ============================================

:: 1. Virtuelle Umgebung anlegen
if not exist ".venv" (
    echo [1/5] Erstelle virtuelle Umgebung...
    python -m venv .venv
) else (
    echo [1/5] Virtuelle Umgebung bereits vorhanden.
)

:: 2. Abhängigkeiten installieren
echo [2/5] Installiere Abhaengigkeiten...
call .venv\Scripts\pip install --quiet --upgrade pip
call .venv\Scripts\pip install --quiet -r requirements.txt
call .venv\Scripts\pip install --quiet pyinstaller

:: 3. GUI-Dateien in gui\ kopieren (erwartet Dateien neben build.bat)
echo [3/5] Kopiere GUI-Dateien...
if not exist "gui" mkdir gui
copy /Y "vereinsverwaltung.html" "gui\" >nul 2>&1
copy /Y "vereinsverwaltung.css"  "gui\" >nul 2>&1
copy /Y "vereinsverwaltung.js"   "gui\" >nul 2>&1

if not exist "gui\vereinsverwaltung.html" (
    echo FEHLER: GUI-Dateien nicht gefunden!
    echo Bitte vereinsverwaltung.html/.css/.js neben build.bat legen.
    pause
    exit /b 1
)

:: 4. PyInstaller ausführen
echo [4/5] Baue .exe mit PyInstaller...
call .venv\Scripts\pyinstaller vereinsverwaltung.spec --noconfirm --clean

:: 5. Ergebnis prüfen
echo [5/5] Pruefe Ergebnis...
if exist "dist\Vereinsverwaltung.exe" (
    echo.
    echo ============================================
    echo  Fertig! dist\Vereinsverwaltung.exe
    echo ============================================
    echo.
    echo Naechste Schritte:
    echo   1. dist\Vereinsverwaltung.exe starten
    echo   2. .env im selben Verzeichnis wie die .exe anlegen
    echo      (Vorlage: .env.example wird beim ersten Start kopiert)
    echo.
) else (
    echo.
    echo FEHLER: Build fehlgeschlagen. Siehe build-Log oben.
)

pause
