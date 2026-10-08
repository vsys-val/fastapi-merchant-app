"""HTTP cache privacy policy over real routes, cookies and error responses."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import create_app
from app.models import Base


ACCOUNT = {"name": "Ana", "email": "ana@example.com", "password": "frase secreta exclusiva 2026"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EMAIL_DELIVERY", "disabled")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://merchant.example.com")
    monkeypatch.setattr("app.auth.consume_attempt", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr("app.auth.active_attempt_count", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr("app.auth.reset_attempts", lambda *_args, **_kwargs: None)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        application = create_app()
        application.dependency_overrides[get_db] = lambda: session
        # No lifespan: these HTTP tests must never start the PostgreSQL metrics writer.
        test_client = TestClient(application, raise_server_exceptions=False)
        try:
            yield test_client
        finally:
            test_client.close()
    engine.dispose()


def test_authentication_and_personal_responses_are_never_stored(client):
    created = client.post("/api/v1/users", json=ACCOUNT)
    logged_in = client.post("/api/v1/auth/login", json={key: ACCOUNT[key] for key in ("email", "password")})
    assert created.status_code == 201
    assert logged_in.status_code == 200
    assert "HttpOnly" in logged_in.headers["set-cookie"]
    profile = client.get("/api/v1/users/me")
    assert profile.status_code == 200
    assert profile.json()["email"] == ACCOUNT["email"]
    logged_out = client.post("/api/v1/auth/logout")
    assert logged_out.status_code == 204
    for response in (created, logged_in, profile, logged_out):
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("method,path,payload,status", [
    ("GET", "/api/v1/products", None, 200),
    ("GET", "/api/v1/users/me", None, 401),
    ("POST", "/api/v1/auth/login", {}, 422),
    ("GET", "/api/v1/missing", None, 404),
    ("PUT", "/api/v1/products", None, 405),
    ("GET", "/api/v1/products/", None, 307),
])
def test_public_reads_errors_and_redirects_are_not_stored(client, method, path, payload, status):
    response = client.request(method, path, json=payload, follow_redirects=False)
    assert response.status_code == status
    assert response.headers["cache-control"] == "no-store"


def test_unexpected_errors_keep_envelope_and_metrics_and_disable_storage(client, monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("private diagnostic")

    monkeypatch.setattr("app.routes.get_product_detail", fail)
    response = client.get("/api/v1/products/42")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private diagnostic" not in response.text
    assert response.headers["cache-control"] == "no-store"
    pending = client.app.state.request_metrics.drain()
    assert any(key[2:] == ("/api/v1/products/{product_id}", 5) for key in pending)


def test_cors_response_headers_are_preserved(client):
    response = client.options("/api/v1/products", headers={
        "Origin": "https://merchant.example.com",
        "Access-Control-Request-Method": "GET",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://merchant.example.com"
    assert "Origin" in response.headers["vary"]
    assert response.headers["cache-control"] == "no-store"


def test_non_api_health_and_schema_remain_unchanged(client):
    for path in ("/health", "/openapi.json"):
        response = client.get(path)
        assert response.status_code == 200
        assert "cache-control" not in response.headers
    pending = client.app.state.request_metrics.drain()
    assert not any(key[2] == "/health" for key in pending)
