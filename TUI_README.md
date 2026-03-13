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

### Browser-GUI

#### Navigation (global)

| Taste | Funktion |
|-------|----------|
| `Alt+1` | Dashboard |
| `Alt+2` | Mitglieder |
| `Alt+3` | Konten |
| `Alt+4` | Buchungen |
| `Alt+5` | T-Konten |
| `Esc` | Modal schließen / T-Konto-Zoom schließen |
| `Enter` | Formular speichern (wenn Modal offen) |

#### Mitglieder

| Taste | Funktion |
|-------|----------|
| `↑` / `↓` | Zeile auswählen |
| `F5` | Neues Mitglied anlegen |
| `F7` | Statuswechsel (nur aktuelle Einträge) |
| `F8` | Ausgewähltes Mitglied löschen |
| `R` | Aktualisieren |

#### Konten

| Taste | Funktion |
|-------|----------|
| `↑` / `↓` | Zeile auswählen |
| `F5` | Neues Konto anlegen |
| `F6` | Ausgewähltes Konto bearbeiten |
| `F8` | Ausgewähltes Konto löschen |
| `R` | Aktualisieren |

#### Buchungen

| Taste | Funktion |
|-------|----------|
| `↑` / `↓` | Zeile auswählen |
| `F5` | Neue Buchung erfassen |
| `F6` | Sammelbuchung öffnen |
| `F7` | Ausgewählte Buchung bearbeiten (Storno & Neu) |
| `F9` | Ausgewählte Buchung kopieren |
| `F8` | Ausgewählte Buchung löschen |
| `G` | Gruppierung umschalten |
| `R` | Aktualisieren |
| `Esc` | Filter zurücksetzen |

#### T-Konten

| Taste | Funktion |
|-------|----------|
| `G` | Gruppierung umschalten |
| `R` | Aktualisieren |

---

### Terminal-UI (TUI)

#### Navigation (global)

| Taste | Funktion |
|-------|----------|
| `F1` | Bereich **Mitglieder** |
| `F2` | Bereich **Konten** |
| `F3` | Bereich **Buchungen** |
| `F4` | Bereich **T-Konten** |
| `Q` | Programm beenden |
| `Tab` / `Shift+Tab` | Fokus weiter / zurück |
| `↑` / `↓` | Zeile in Tabelle navigieren |
| `Esc` | Modaldialog schließen / Abbrechen |

#### Mitglieder

| Taste | Funktion |
|-------|----------|
| `F5` | Neues Mitglied anlegen |
| `F6` | Ausgewähltes Mitglied **bearbeiten** (Name, Status, Datum) |
| `F7` | **Statuswechsel** historisiert erfassen |
| `F8` | Ausgewähltes Mitglied löschen (mit Bestätigung) |
| `R` | Liste aktualisieren |

> `F7` ist nur für aktuell gültige Einträge möglich (ohne „Bis"-Datum).

#### Konten

| Taste | Funktion |
|-------|----------|
| `F5` | Neues Konto anlegen |
| `F6` | Ausgewähltes Konto **bearbeiten** (Nummer, Name) |
| `F8` | Ausgewähltes Konto löschen (mit Bestätigung) |
| `R` | Liste aktualisieren |

#### Buchungen

| Taste | Funktion |
|-------|----------|
| `F5` | Neue Buchung erfassen |
| `F6` | **Storno & Neubuchung** – storniert die aktuelle Buchung und öffnet ein neues Formular |
| `F7` | Buchung **kopieren** (Datum wird auf heute gesetzt) |
| `F8` | Buchung löschen (mit Bestätigung) |
| `G` | Buchungen **gruppieren** / Gruppierung aufheben |
| `R` | Liste aktualisieren |

> Filter (Von/Bis/Konto/Mitglied): Eingabe + „Suchen" oder `R`. „✕" setzt alle Filter zurück.  
> Gruppieren fasst Buchungen mit gleichem Soll-/Habenkonto, Datum und Text zusammen (`[3×]`).

#### T-Konten

| Taste | Funktion |
|-------|----------|
| `R` | Aktualisieren |

#### Modaldialoge

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
