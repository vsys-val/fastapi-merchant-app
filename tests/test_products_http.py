import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import get_db
from app.main import create_app
from app.models import Base, User


@pytest.fixture
def product_client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    user = User(public_name="Valério", email="valerio@example.com", password_hash="hash")
    session.add(user)
    session.commit()

    application = create_app()
    application.dependency_overrides[get_db] = lambda: session
    application.dependency_overrides[get_current_user] = lambda: user
    with TestClient(application) as client:
        yield client
    session.close()
    Base.metadata.drop_all(engine)


def payload():
    return {
        "name": "Café torrado",
        "brand": "Marca X",
        "quantity": 1.5,
        "unit": "kg",
        "category": "food",
        "barcode": "7891000100103",
    }


def test_product_http_create_conflict_delete_and_reactivate(product_client):
    created = product_client.post("/api/v1/products", json=payload())
    assert created.status_code == 201
    assert created.json()["quantity"] == 1500
    assert created.json()["unit"] == "g"
    assert set(created.json()) == {
        "id", "name", "brand", "variant", "quantity", "unit", "category", "barcode"
    }

    conflict = product_client.post("/api/v1/products", json=payload())
    assert conflict.status_code == 409
    assert conflict.json()["error"]["details"] == {
        "existing_product_id": created.json()["id"]
    }

    deleted = product_client.delete(f"/api/v1/products/{created.json()['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""

    repeated = product_client.delete(f"/api/v1/products/{created.json()['id']}")
    assert repeated.status_code == 404

    reactivated = product_client.post("/api/v1/products", json=payload())
    assert reactivated.status_code == 200
    assert reactivated.json()["id"] == created.json()["id"]


def test_product_http_patch_and_validation_envelope(product_client):
    created = product_client.post("/api/v1/products", json=payload()).json()
    updated = product_client.patch(
        f"/api/v1/products/{created['id']}",
        json={"variant": " Tradicional ", "barcode": None},
    )
    assert updated.status_code == 200
    assert updated.json()["variant"] == "Tradicional"
    assert updated.json()["barcode"] is None

    invalid = product_client.patch(f"/api/v1/products/{created['id']}", json={})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
