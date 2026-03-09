import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# In-Memory SQLite für Tests
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


def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_item():
    r = client.post("/items/", json={"name": "Test", "description": "Beschreibung"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test"
    assert data["id"] is not None


def test_get_items():
    client.post("/items/", json={"name": "Item 1"})
    client.post("/items/", json={"name": "Item 2"})
    r = client.get("/items/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_single_item():
    created = client.post("/items/", json={"name": "Einzeln"}).json()
    r = client.get(f"/items/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Einzeln"


def test_update_item():
    created = client.post("/items/", json={"name": "Alt"}).json()
    r = client.put(f"/items/{created['id']}", json={"name": "Neu"})
    assert r.status_code == 200
    assert r.json()["name"] == "Neu"


def test_delete_item():
    created = client.post("/items/", json={"name": "Löschen"}).json()
    r = client.delete(f"/items/{created['id']}")
    assert r.status_code == 204
    r2 = client.get(f"/items/{created['id']}")
    assert r2.status_code == 404


def test_item_not_found():
    r = client.get("/items/9999")
    assert r.status_code == 404
