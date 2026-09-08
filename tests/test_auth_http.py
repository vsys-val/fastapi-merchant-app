from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.auth import current_user_response
from app.database import get_db
from app.main import create_app
from app.schemas import UserPublic


@pytest.fixture
def application(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    return app


def test_register_returns_201_without_password_or_hash(application, monkeypatch):
    monkeypatch.setattr(
        "app.routes.create_user",
        lambda payload, _session: UserPublic(id=7, name=payload.name, email=payload.email),
    )
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/users",
            json={
                "email": "VALERIO@example.com",
                "name": "Valério",
                "password": "uma frase secreta longa",
            },
        )
    assert response.status_code == 201
    assert response.json() == {"id": 7, "name": "Valério", "email": "valerio@example.com"}
    assert "password" not in response.text
    assert "hash" not in response.text


def test_login_returns_contract_token_shape(application, monkeypatch):
    from app.schemas import TokenResponse

    monkeypatch.setattr(
        "app.routes.login",
        lambda _payload, _request, _session: TokenResponse(access_token="signed.jwt.token"),
    )
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "valerio@example.com", "password": "qualquer senha"},
        )
    assert response.status_code == 200
    assert response.json() == {
        "access_token": "signed.jwt.token",
        "token_type": "bearer",
        "expires_in": 86400,
    }


def test_users_me_requires_bearer_token(application):
    with TestClient(application) as client:
        response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "invalid_authentication"


def test_users_me_returns_only_private_account_fields(application):
    application.dependency_overrides[current_user_response] = lambda: UserPublic(
        id=9, name="Valério", email="valerio@example.com"
    )
    with TestClient(application) as client:
        response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json() == {"id": 9, "name": "Valério", "email": "valerio@example.com"}
