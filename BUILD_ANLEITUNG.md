# Vereinsverwaltung – Windows EXE Build

## Voraussetzungen

| Was | Version |
|-----|---------|
| Python | 3.11 oder 3.12 (64-bit) |
| pip | aktuell (wird vom Skript aktualisiert) |
| Windows | 10 / 11 |

Python: https://www.python.org/downloads/  
→ Bei der Installation **"Add Python to PATH"** aktivieren.

---

## Schritt 1 – Dateien vorbereiten

Folgende Dateien müssen alle im **selben Verzeichnis** liegen:

```
vereinsverwaltung/
├── app/                        ← API-Quellcode (aus api_project.zip)
├── tests/
├── .env.example
├── requirements.txt
├── launcher.py
├── vereinsverwaltung.spec
├── build.bat
├── vereinsverwaltung.html      ← GUI-Dateien
├── vereinsverwaltung.css
└── vereinsverwaltung.js
```

---

## Schritt 2 – Build ausführen

Doppelklick auf **`build.bat`** oder in der Kommandozeile:

```bat
cd C:\Pfad\zu\vereinsverwaltung
build.bat
```

Der Build dauert ca. 1–3 Minuten. Am Ende liegt die fertige Datei unter:

```
dist\Vereinsverwaltung.exe
```

---

## Schritt 3 – Verteilen

Kopiere aus dem `dist\`-Verzeichnis **nur**:

```
Vereinsverwaltung.exe
```

Die `.exe` ist vollständig selbstständig – kein Python, kein Installieren nötig.

---

## Schritt 4 – Konfiguration (.env)

Beim ersten Start wird automatisch eine `.env`-Datei **neben der .exe** angelegt  
(Kopie der `.env.example`). Diese Datei bearbeiten:

```env
# Lokale Datenbank-Datei (Standard)
DB_SOURCE=local
LOCAL_DB_PATH=./data.db

# Oder: FTP-Sync
# DB_SOURCE=ftp
# FTP_HOST=ftp.meinverein.de
# FTP_USER=benutzer
# FTP_PASSWORD=passwort
# FTP_PATH=/vereinsverwaltung/data.db
```

Die `.env` und `data.db` liegen neben der `.exe` – dort auch Backups ablegen.

---

## Wie die .exe funktioniert

```
Vereinsverwaltung.exe startet
  │
  ├─ FastAPI-API auf Port 8765 (oder nächster freier Port)
  ├─ GUI-Dateien werden in gui\ neben der .exe bereitgestellt
  ├─ API-URL in vereinsverwaltung.js wird automatisch angepasst
  └─ Standard-Browser öffnet sich mit der GUI
```

Ein **Tray-Icon** erscheint in der Windows-Taskleiste (falls `pystray` + `Pillow`  
installiert sind – optional, sonst läuft die App im Hintergrund weiter).  
Zum Beenden: Tray-Icon → *Beenden*, oder Task-Manager.

---

## Optionales: Tray-Icon aktivieren

Für ein System-Tray-Icon vor dem Build installieren:

```bat
.venv\Scripts\pip install pystray Pillow
```

Dann Build erneut ausführen.

---

## Optionales: Eigenes Icon

Eine `.ico`-Datei erstellen und in `vereinsverwaltung.spec` eintragen:

```python
# Zeile in der EXE()-Sektion einkommentieren:
icon="mein_icon.ico",
```

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| „Python nicht gefunden" | Python neu installieren, PATH-Option aktivieren |
| Build schlägt fehl bei `pydantic` | `.venv\Scripts\pip install pydantic==2.7.0` |
| Browser öffnet sich nicht | `gui\vereinsverwaltung.html` manuell im Browser öffnen |
| API antwortet nicht | Prüfen ob Port 8765 von Firewall blockiert wird |
| .exe wird von Antivirus blockiert | PyInstaller-EXEs lösen manchmal Fehlalarm aus – Ausnahme hinzufügen |
