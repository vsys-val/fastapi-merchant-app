"""Sessão do navegador em cookie HttpOnly (ADR-0016), com banco SQLite real."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import create_app
from app.models import Base
from app.session_cookie import COOKIE_NAME, CSRF_HEADER

ACCOUNT = {"name": "Ana", "email": "ana@example.com", "password": "frase secreta exclusiva 2026"}
PRODUCT = {"name": "Café torrado", "brand": "Pilão", "quantity": "500", "unit": "g", "category": "food"}
WRITE = {CSRF_HEADER: "web"}


def _client(monkeypatch, tmp_path, environment="development"):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("EMAIL_DELIVERY", "disabled")
    monkeypatch.setattr("app.auth.consume_attempt", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr("app.auth.active_attempt_count", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr("app.auth.reset_attempts", lambda *_args, **_kwargs: None)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    application = create_app()
    application.dependency_overrides[get_db] = lambda: session
    return TestClient(application)


@pytest.fixture
def client(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as test_client:
        assert test_client.post("/api/v1/users", json=ACCOUNT).status_code == 201
        yield test_client


def _login(client):
    return client.post("/api/v1/auth/login", json={"email": ACCOUNT["email"], "password": ACCOUNT["password"]})


def test_login_sets_an_httponly_session_cookie(client):
    response = _login(client)
    header = response.headers["set-cookie"]
    assert response.status_code == 200
    assert header.startswith(f"{COOKIE_NAME}=")
    assert "HttpOnly" in header
    assert "Path=/api" in header
    assert "SameSite=lax" in header
    assert "Max-Age=86400" in header
    # O corpo continua trazendo o token para clientes de API.
    assert response.json()["token_type"] == "bearer"


def test_cookie_is_secure_in_production(monkeypatch, tmp_path):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://merchant-app-web.onrender.com")
    with _client(monkeypatch, tmp_path, environment="production") as client:
        client.post("/api/v1/users", json=ACCOUNT)
        assert "Secure" in _login(client).headers["set-cookie"]


def test_cookie_authenticates_reads_and_writes_with_the_csrf_header(client):
    _login(client)
    assert client.get("/api/v1/users/me").json()["email"] == ACCOUNT["email"]

    refused = client.post("/api/v1/products", json=PRODUCT)
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "csrf_header_required"

    assert client.post("/api/v1/products", json=PRODUCT, headers=WRITE).status_code == 201


def test_logout_clears_the_cookie(client):
    _login(client)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert f'{COOKIE_NAME}=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]
    assert client.get("/api/v1/users/me").status_code == 401


def test_expired_cookie_keeps_public_reads_anonymous(client):
    client.cookies.set(COOKIE_NAME, "token.invalido", path="/api")
    assert client.get("/api/v1/products").status_code == 200
    assert client.get("/api/v1/users/me").status_code == 401


def test_bearer_token_is_exchanged_for_the_cookie(client):
    token = _login(client).json()["access_token"]
    client.cookies.clear()

    assert client.post("/api/v1/auth/session").status_code == 401
    assert client.post("/api/v1/auth/session", headers={"Authorization": "Bearer invalido"}).status_code == 401

    exchanged = client.post("/api/v1/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert exchanged.status_code == 204
    assert exchanged.headers["set-cookie"].startswith(f"{COOKIE_NAME}=")
    assert client.get("/api/v1/users/me").json()["email"] == ACCOUNT["email"]


def test_bearer_header_still_works_without_csrf_header(client):
    token = _login(client).json()["access_token"]
    client.cookies.clear()
    response = client.post("/api/v1/products", json=PRODUCT, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
