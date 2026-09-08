from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import create_app
from app.models import Base


def test_complete_api_journey_with_real_authentication(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:password@localhost/test_db",
    )
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    monkeypatch.setattr("app.auth.consume_attempt", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr("app.auth.active_attempt_count", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr("app.auth.reset_attempts", lambda *_args, **_kwargs: None)

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
    application = create_app()
    application.dependency_overrides[get_db] = lambda: session

    account = {
        "name": "Valério",
        "email": "valerio@example.com",
        "password": "frase secreta exclusiva 2026",
    }
    product_payload = {
        "name": "Café torrado especial",
        "brand": "Serra Brasileira",
        "variant": "Torra média",
        "quantity": "1,5",
        "unit": "kg",
        "category": "food",
    }
    review_payload = {
        "repurchase_intent": "yes",
        "quality": "high",
        "expectation": "exceeded",
        "value_for_money": "good",
        "reasons": [{"aspect": "taste", "perception": "positive"}],
        "comment": "Sabor equilibrado e boa torra.",
    }

    with TestClient(application) as client:
        registered = client.post("/api/v1/users", json=account)
        assert registered.status_code == 201
        assert registered.json()["email"] == account["email"]
        assert "password" not in registered.text

        authenticated = client.post(
            "/api/v1/auth/login",
            json={"email": account["email"], "password": account["password"]},
        )
        assert authenticated.status_code == 200
        assert authenticated.json()["expires_in"] == 86400
        headers = {
            "Authorization": f"Bearer {authenticated.json()['access_token']}"
        }
        assert client.get("/api/v1/users/me", headers=headers).json()["name"] == "Valério"

        created_product = client.post(
            "/api/v1/products", json=product_payload, headers=headers
        )
        assert created_product.status_code == 201
        product = created_product.json()
        assert (product["quantity"], product["unit"]) == (1500, "g")

        created_review = client.post(
            f"/api/v1/products/{product['id']}/reviews",
            json=review_payload,
            headers=headers,
        )
        assert created_review.status_code == 201
        review = created_review.json()

        public_detail = client.get(f"/api/v1/products/{product['id']}")
        assert public_detail.status_code == 200
        assert public_detail.json()["community_summary"]["total_reviews"] == 1
        assert public_detail.json()["your_review"] is None

        private_detail = client.get(
            f"/api/v1/products/{product['id']}", headers=headers
        )
        assert private_detail.json()["community_summary"]["total_reviews"] == 0
        assert private_detail.json()["your_review"]["id"] == review["id"]

        own_products = client.get("/api/v1/users/me/products", headers=headers)
        own_reviews = client.get("/api/v1/users/me/reviews", headers=headers)
        assert own_products.json()["items"][0]["id"] == product["id"]
        assert own_reviews.json()["items"][0]["id"] == review["id"]

        updated_review = client.patch(
            f"/api/v1/reviews/{review['id']}",
            json={"quality": "adequate"},
            headers=headers,
        )
        assert updated_review.status_code == 200
        assert updated_review.json()["quality"] == "adequate"

        assert (
            client.delete(f"/api/v1/reviews/{review['id']}", headers=headers).status_code
            == 204
        )
        assert (
            client.delete(f"/api/v1/products/{product['id']}", headers=headers).status_code
            == 204
        )
        empty_search = client.get("/api/v1/products?name=cafe")
        assert empty_search.status_code == 200
        assert empty_search.json()["items"] == []
        assert empty_search.json()["total"] == 0

    session.close()
    Base.metadata.drop_all(engine)
