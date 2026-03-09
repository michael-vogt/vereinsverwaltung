# 🚀 FastAPI + SQLite Starter

Python REST API mit FastAPI, SQLAlchemy ORM und SQLite als Datenbank.

## Projektstruktur

```
api_project/
├── app/
│   ├── main.py          # FastAPI-App & Router-Registrierung
│   ├── database.py      # SQLite-Verbindung & Session
│   ├── models/
│   │   └── item.py      # SQLAlchemy ORM-Modell
│   ├── schemas/
│   │   └── item.py      # Pydantic-Schemas (Request/Response)
│   └── routers/
│       └── items.py     # CRUD-Endpunkte
├── tests/
│   └── test_items.py    # Pytest-Tests
├── requirements.txt
└── README.md
```

## Setup

```bash
# Virtuelle Umgebung erstellen
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Server starten
uvicorn app.main:app --reload
```

## API-Dokumentation

Nach dem Start erreichbar unter:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:**       http://localhost:8000/redoc

## Endpunkte

| Methode | Pfad           | Beschreibung            |
|---------|----------------|-------------------------|
| GET     | /items/        | Alle Items abrufen      |
| GET     | /items/{id}    | Ein Item abrufen        |
| POST    | /items/        | Neues Item erstellen    |
| PUT     | /items/{id}    | Item aktualisieren      |
| DELETE  | /items/{id}    | Item löschen            |

## Tests ausführen

```bash
pytest tests/ -v
```

## Neues Modell hinzufügen

1. `app/models/meinmodell.py` – SQLAlchemy-Klasse definieren
2. `app/schemas/meinmodell.py` – Pydantic-Schemas erstellen
3. `app/routers/meinmodell.py` – CRUD-Router implementieren
4. In `app/main.py` einbinden: `app.include_router(...)`
