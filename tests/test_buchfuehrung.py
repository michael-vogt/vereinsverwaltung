import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_konto(nummer="1000", name="Kasse"):
    return client.post("/konten/", json={"kontonummer": nummer, "kontoname": name}).json()


def make_buchung(soll_id, haben_id, betrag="100.00", datum="2025-03-01", text="Test", mitglied_id=None):
    payload = {
        "sollkonto_id": soll_id,
        "habenkonto_id": haben_id,
        "betrag": betrag,
        "buchungsdatum": datum,
        "buchungstext": text,
        "mitglied_id": mitglied_id,
    }
    return client.post("/buchungen/", json=payload)


# ---------------------------------------------------------------------------
# Kontenrahmen
# ---------------------------------------------------------------------------

def test_create_konto():
    r = client.post("/konten/", json={"kontonummer": "1000", "kontoname": "Kasse"})
    assert r.status_code == 201
    assert r.json()["kontonummer"] == "1000"


def test_duplicate_kontonummer():
    make_konto("1000")
    r = client.post("/konten/", json={"kontonummer": "1000", "kontoname": "Doppelt"})
    assert r.status_code == 409


def test_get_konten():
    make_konto("1000", "Kasse")
    make_konto("1200", "Bank")
    r = client.get("/konten/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_update_konto():
    k = make_konto("1000", "Alt")
    r = client.put(f"/konten/{k['id']}", json={"kontoname": "Neu"})
    assert r.status_code == 200
    assert r.json()["kontoname"] == "Neu"


def test_delete_konto_in_use():
    k1 = make_konto("1000", "Kasse")
    k2 = make_konto("1200", "Bank")
    make_buchung(k1["id"], k2["id"])
    r = client.delete(f"/konten/{k1['id']}")
    assert r.status_code == 409


def test_delete_konto_unused():
    k = make_konto("9999", "Unbenutzt")
    r = client.delete(f"/konten/{k['id']}")
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Buchungen
# ---------------------------------------------------------------------------

def test_create_buchung():
    k1 = make_konto("1000", "Kasse")
    k2 = make_konto("1200", "Bank")
    r = make_buchung(k1["id"], k2["id"])
    assert r.status_code == 201
    data = r.json()
    assert data["betrag"] == "100.00"
    assert data["sollkonto"]["kontonummer"] == "1000"
    assert data["habenkonto"]["kontonummer"] == "1200"


def test_soll_haben_identisch():
    k = make_konto("1000", "Kasse")
    r = make_buchung(k["id"], k["id"])
    assert r.status_code == 422


def test_buchung_invalid_konto():
    k = make_konto("1000", "Kasse")
    r = make_buchung(k["id"], 9999)
    assert r.status_code == 422


def test_filter_buchungen_by_datum():
    k1 = make_konto("1000", "Kasse")
    k2 = make_konto("1200", "Bank")
    make_buchung(k1["id"], k2["id"], datum="2025-01-01")
    make_buchung(k1["id"], k2["id"], datum="2025-06-01")
    r = client.get("/buchungen/?von=2025-05-01")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_filter_buchungen_by_konto():
    k1 = make_konto("1000", "Kasse")
    k2 = make_konto("1200", "Bank")
    k3 = make_konto("4000", "Beiträge")
    make_buchung(k1["id"], k2["id"])
    make_buchung(k2["id"], k3["id"])
    r = client.get(f"/buchungen/?konto_id={k1['id']}")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_buchung_mit_mitglied():
    k1 = make_konto("1000", "Kasse")
    k2 = make_konto("4000", "Beiträge")
    mitglied = client.post("/members/", json={
        "name": "Max Mustermann", "status": "aktiv", "gueltig_von": "2023-01-01"
    }).json()
    r = make_buchung(k1["id"], k2["id"], mitglied_id=mitglied["id"])
    assert r.status_code == 201
    assert r.json()["mitglied"]["name"] == "Max Mustermann"


def test_update_buchung():
    k1 = make_konto("1000", "Kasse")
    k2 = make_konto("1200", "Bank")
    b = make_buchung(k1["id"], k2["id"], text="Alt").json()
    r = client.put(f"/buchungen/{b['id']}", json={"buchungstext": "Korrigiert"})
    assert r.status_code == 200
    assert r.json()["buchungstext"] == "Korrigiert"


def test_delete_buchung():
    k1 = make_konto("1000", "Kasse")
    k2 = make_konto("1200", "Bank")
    b = make_buchung(k1["id"], k2["id"]).json()
    r = client.delete(f"/buchungen/{b['id']}")
    assert r.status_code == 204
