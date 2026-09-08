import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import get_db
from app.main import create_app
from app.models import Base, User


@pytest.fixture
def review_client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    owner = User(public_name="Valério", email="owner@example.com", password_hash="hash")
    other = User(public_name="Outra pessoa", email="other@example.com", password_hash="hash")
    session.add_all([owner, other])
    session.commit()
    identity = {"user": owner}

    application = create_app()
    application.dependency_overrides[get_db] = lambda: session
    application.dependency_overrides[get_current_user] = lambda: identity["user"]
    with TestClient(application) as client:
        yield client, identity, owner, other
    session.close()
    Base.metadata.drop_all(engine)


def product_payload():
    return {
        "name": "Café torrado",
        "brand": "Marca X",
        "quantity": 500,
        "unit": "g",
        "category": "food",
    }


def review_payload(**changes):
    values = {
        "repurchase_intent": "yes",
        "quality": "high",
        "expectation": "met",
        "value_for_money": "good",
        "reasons": [{"aspect": "taste", "perception": "positive"}],
        "comment": "Compraria novamente.",
    }
    values.update(changes)
    return values


def test_review_http_full_lifecycle(review_client):
    client, _, _, _ = review_client
    product = client.post("/api/v1/products", json=product_payload()).json()
    created = client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json=review_payload(),
    )
    assert created.status_code == 201
    body = created.json()
    assert set(body) == {
        "id",
        "repurchase_intent",
        "quality",
        "expectation",
        "value_for_money",
        "reasons",
        "comment",
        "created_at",
        "updated_at",
    }
    assert body["reasons"] == [{"aspect": "taste", "perception": "positive"}]

    duplicate = client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json=review_payload(),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["details"] == {"existing_review_id": body["id"]}

    updated = client.patch(
        f"/api/v1/reviews/{body['id']}",
        json={
            "quality": "adequate",
            "reasons": [{"aspect": "taste", "perception": "negative"}],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["quality"] == "adequate"
    assert updated.json()["reasons"][0]["perception"] == "negative"
    assert updated.json()["created_at"] == body["created_at"]

    deleted = client.delete(f"/api/v1/reviews/{body['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.delete(f"/api/v1/reviews/{body['id']}").status_code == 404


def test_review_http_authorship_and_final_state_validation(review_client):
    client, identity, owner, other = review_client
    product = client.post("/api/v1/products", json=product_payload()).json()
    review = client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json=review_payload(comment=None),
    ).json()

    invalid = client.patch(
        f"/api/v1/reviews/{review['id']}",
        json={"reasons": [{"aspect": "other", "perception": "negative"}]},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    empty = client.patch(f"/api/v1/reviews/{review['id']}", json={})
    assert empty.status_code == 422
    identity["user"] = other
    assert client.patch(
        f"/api/v1/reviews/{review['id']}", json={"quality": "low"}
    ).status_code == 403
    assert client.delete(f"/api/v1/reviews/{review['id']}").status_code == 403
    identity["user"] = owner


def test_review_http_rejects_inactive_product(review_client):
    client, _, _, _ = review_client
    product = client.post("/api/v1/products", json=product_payload()).json()
    assert client.delete(f"/api/v1/products/{product['id']}").status_code == 204
    response = client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json=review_payload(),
    )
    assert response.status_code == 404
