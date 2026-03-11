# Vereinsverwaltung – Terminal UI (TUI)

Konsolenbasierte Benutzeroberfläche für die Vereinsverwaltung.  
Spricht direkt gegen die FastAPI-Backend-API.

## Voraussetzungen

```bash
pip install textual>=8.0.0 httpx
```

## Starten

```bash
# Standard (API auf localhost:8000)
python tui.py

# Andere API-URL
python tui.py --api http://localhost:8765
```

---

## Tastaturbelegung

### Navigation (immer aktiv)

| Taste | Funktion |
|-------|----------|
| `F1` | Bereich **Mitglieder** |
| `F2` | Bereich **Konten** |
| `F3` | Bereich **Buchungen** |
| `Q` | Programm beenden |
| `Tab` | Fokus zum nächsten Element |
| `Shift+Tab` | Fokus zum vorherigen Element |
| `↑` / `↓` | Zeile in Tabelle navigieren |
| `Esc` | Modaldialog schließen / Abbrechen |

---

### Bereich: Mitglieder

| Taste | Funktion |
|-------|----------|
| `F5` | Neues Mitglied anlegen |
| `F6` | Ausgewähltes Mitglied **bearbeiten** (Name, Status, Datum) |
| `F7` | **Statuswechsel** historisiert erfassen |
| `F8` | Ausgewähltes Mitglied löschen (mit Bestätigung) |
| `R` | Liste aktualisieren |

> **Hinweis:** Der Statuswechsel (F7) ist nur für aktuell gültige Einträge möglich  
> (Einträge ohne „Bis"-Datum). Er legt automatisch einen historisierten Eintrag an.

---

### Bereich: Konten

| Taste | Funktion |
|-------|----------|
| `F5` | Neues Konto anlegen |
| `F6` | Ausgewähltes Konto **bearbeiten** (Nummer, Name) |
| `F8` | Ausgewähltes Konto löschen (mit Bestätigung) |
| `R` | Liste aktualisieren |

---

### Bereich: Buchungen

| Taste | Funktion |
|-------|----------|
| `F5` | Neue Buchung erfassen |
| `F6` | **Storno & Neubuchung** – storniert die aktuelle Buchung und öffnet ein neues Formular |
| `F7` | Buchung **kopieren** (Datum wird auf heute gesetzt) |
| `F8` | Buchung löschen (mit Bestätigung) |
| `G` | Buchungen **gruppieren** / Gruppierung aufheben |
| `R` | Liste aktualisieren |

#### Filter

Die Filterleiste (Von / Bis / Konto / Mitglied) wird mit **„Suchen"** ausgeführt  
oder durch Drücken von `R`. **„✕"** setzt alle Filter zurück.

#### Gruppieren

Buchungen mit gleichem Soll-/Habenkonto, Datum und Text werden  
zu einer Zeile zusammengefasst. Betrag = Summe, Anzahl = `[3×]`.

---

### Modaldialoge

| Taste | Funktion |
|-------|----------|
| `Enter` | Formular absenden / Ja bestätigen |
| `Esc` | Dialog schließen / Abbrechen / Nein |
| `Tab` | Nächstes Feld |

---

## Datenfluss

```
tui.py  ──HTTP──►  FastAPI (app/main.py)  ──►  SQLite-Datenbank
```

Alle Änderungen in der TUI sind sofort auch im Browser-Frontend sichtbar  
(gleiches Backend, gleiche Daten).

## Konfiguration

Die TUI verwendet keine eigene `.env`-Datei.  
Die API-URL wird beim Start übergeben:

```bash
python tui.py --api http://localhost:8000
```
