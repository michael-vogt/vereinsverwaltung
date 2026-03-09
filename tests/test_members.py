import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, timedelta

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

MEMBER_PAYLOAD = {
    "name": "Max Mustermann",
    "status": "aktiv",
    "gueltig_von": "2023-01-01",
    "gueltig_bis": None,
}


def test_health():
    r = client.get("/")
    assert r.status_code == 200


def test_create_member():
    r = client.post("/members/", json=MEMBER_PAYLOAD)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Max Mustermann"
    assert data["status"] == "aktiv"
    assert data["gueltig_bis"] is None


def test_get_members_nur_aktuell():
    client.post("/members/", json=MEMBER_PAYLOAD)
    # Historisierter Eintrag (gueltig_bis gesetzt)
    old = {**MEMBER_PAYLOAD, "gueltig_von": "2020-01-01", "gueltig_bis": "2022-12-31"}
    client.post("/members/", json=old)
    r = client.get("/members/?nur_aktuell=true")
    assert r.status_code == 200
    assert all(m["gueltig_bis"] is None for m in r.json())


def test_get_members_alle():
    client.post("/members/", json=MEMBER_PAYLOAD)
    old = {**MEMBER_PAYLOAD, "gueltig_von": "2020-01-01", "gueltig_bis": "2022-12-31"}
    client.post("/members/", json=old)
    r = client.get("/members/?nur_aktuell=false")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_status_update_historisiert():
    created = client.post("/members/", json=MEMBER_PAYLOAD).json()
    r = client.put(
        f"/members/{created['id']}/status",
        json={"neuer_status": "passiv", "gueltig_ab": "2025-06-01"},
    )
    assert r.status_code == 200
    new_entry = r.json()
    assert new_entry["status"] == "passiv"
    assert new_entry["gueltig_von"] == "2025-06-01"
    assert new_entry["gueltig_bis"] is None

    # Alter Eintrag muss jetzt gueltig_bis haben
    old = client.get(f"/members/{created['id']}").json()
    assert old["gueltig_bis"] == "2025-05-31"


def test_status_update_invalid_date():
    created = client.post("/members/", json=MEMBER_PAYLOAD).json()
    r = client.put(
        f"/members/{created['id']}/status",
        json={"neuer_status": "passiv", "gueltig_ab": "2022-01-01"},  # vor gueltig_von
    )
    assert r.status_code == 422


def test_delete_member():
    created = client.post("/members/", json=MEMBER_PAYLOAD).json()
    r = client.delete(f"/members/{created['id']}")
    assert r.status_code == 204
    assert client.get(f"/members/{created['id']}").status_code == 404


def test_filter_by_status():
    client.post("/members/", json=MEMBER_PAYLOAD)
    client.post("/members/", json={**MEMBER_PAYLOAD, "name": "Anna Schmidt", "status": "passiv"})
    r = client.get("/members/?mitglied_status=passiv")
    assert r.status_code == 200
    assert all(m["status"] == "passiv" for m in r.json())
