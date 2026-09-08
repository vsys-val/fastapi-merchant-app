import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.main import create_app
from app.models import Base, User


@pytest.fixture
def catalog_client(monkeypatch, tmp_path):
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
    owner = User(public_name="Valério", email="owner@example.com", password_hash="hash")
    other = User(public_name="Ana", email="ana@example.com", password_hash="hash")
    session.add_all([owner, other])
    session.commit()
    identity = {"required": owner, "optional": owner}

    application = create_app()
    application.dependency_overrides[get_db] = lambda: session
    application.dependency_overrides[get_current_user] = lambda: identity["required"]
    application.dependency_overrides[get_optional_user] = lambda: identity["optional"]
    with TestClient(application) as client:
        yield client, identity, owner, other
    session.close()
    Base.metadata.drop_all(engine)


def product_payload(name="Açaí tradicional", brand="Sabor Brasil"):
    return {
        "name": name,
        "brand": brand,
        "quantity": 500,
        "unit": "g",
        "category": "food",
    }


def review_payload(intent):
    return {
        "repurchase_intent": intent,
        "quality": "high",
        "expectation": "met",
        "value_for_money": "good",
        "reasons": [{"aspect": "taste", "perception": "positive"}],
    }


def test_public_and_authenticated_catalog_views(catalog_client):
    client, identity, owner, other = catalog_client
    product = client.post("/api/v1/products", json=product_payload()).json()
    own = client.post(
        f"/api/v1/products/{product['id']}/reviews", json=review_payload("yes")
    ).json()
    identity["required"] = other
    identity["optional"] = other
    community = client.post(
        f"/api/v1/products/{product['id']}/reviews", json=review_payload("no")
    ).json()

    identity["optional"] = None
    listed = client.get("/api/v1/products?name=acai")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["community_summary"]["total_reviews"] == 2
    assert listed.json()["items"][0]["your_repurchase_intent"] is None
    detail = client.get(f"/api/v1/products/{product['id']}").json()
    assert detail["community_summary"]["total_reviews"] == 2
    assert detail["your_review"] is None
    public_reviews = client.get(f"/api/v1/products/{product['id']}/reviews").json()
    assert public_reviews["total"] == 2
    assert {item["author_name"] for item in public_reviews["items"]} == {"Valério", "Ana"}
    assert all("email" not in item and "author_id" not in item for item in public_reviews["items"])

    identity["optional"] = owner
    listed = client.get("/api/v1/products?name=açaí").json()["items"][0]
    assert listed["community_summary"]["total_reviews"] == 1
    assert listed["your_repurchase_intent"] == "yes"
    detail = client.get(f"/api/v1/products/{product['id']}").json()
    assert detail["your_review"]["id"] == own["id"]
    reviews = client.get(f"/api/v1/products/{product['id']}/reviews").json()
    assert reviews["total"] == 1
    assert reviews["items"][0]["id"] == community["id"]


def test_personal_lists_and_query_validation(catalog_client):
    client, identity, owner, _ = catalog_client
    identity["required"] = owner
    identity["optional"] = owner
    product = client.post("/api/v1/products", json=product_payload()).json()
    review = client.post(
        f"/api/v1/products/{product['id']}/reviews", json=review_payload("yes")
    ).json()
    own_reviews = client.get("/api/v1/users/me/reviews?page=1&page_size=20")
    assert own_reviews.status_code == 200
    assert own_reviews.json()["items"][0]["id"] == review["id"]
    assert own_reviews.json()["items"][0]["product"]["id"] == product["id"]
    own_products = client.get("/api/v1/users/me/products")
    assert own_products.status_code == 200
    assert own_products.json()["items"][0]["id"] == product["id"]

    invalid_urls = [
        "/api/v1/products?name=a",
        "/api/v1/products?page=0",
        "/api/v1/products?page_size=101",
        "/api/v1/products?category=food&category=cleaning",
        "/api/v1/products?category=invalid",
        "/api/v1/products?barcode=7891000100103&name=acai",
    ]
    for url in invalid_urls:
        response = client.get(url)
        assert response.status_code == 422, url
        assert response.json()["error"]["code"] == "validation_error"


def test_inactive_product_is_hidden_from_all_catalog_reads(catalog_client):
    client, _, _, _ = catalog_client
    product = client.post("/api/v1/products", json=product_payload()).json()
    assert client.delete(f"/api/v1/products/{product['id']}").status_code == 204
    assert client.get("/api/v1/products").json()["items"] == []
    assert client.get(f"/api/v1/products/{product['id']}").status_code == 404
    assert client.get(f"/api/v1/products/{product['id']}/reviews").status_code == 404


def test_optional_auth_accepts_absence_but_rejects_invalid_token(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    application = create_app()
    application.dependency_overrides[get_db] = lambda: session
    with TestClient(application) as client:
        assert client.get("/api/v1/products").status_code == 200
        invalid = client.get(
            "/api/v1/products",
            headers={"Authorization": "Bearer token-invalido"},
        )
        assert invalid.status_code == 401
        assert invalid.json()["error"]["code"] == "invalid_authentication"
        wrong_scheme = client.get(
            "/api/v1/products",
            headers={"Authorization": "Basic credenciais"},
        )
        assert wrong_scheme.status_code == 401
    session.close()
    Base.metadata.drop_all(engine)
