import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import ProductCreate


@pytest.fixture(autouse=True)
def configured_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db"
    )
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)


def test_fastapi_validation_uses_public_error_envelope():
    application: FastAPI = create_app()

    @application.post("/probe")
    def probe(_product: ProductCreate):
        return None

    with TestClient(application) as client:
        response = client.post("/probe", json={"name": "x"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Os dados enviados são inválidos."
    assert all(set(item) == {"field", "code", "message"} for item in payload["error"]["details"])
    assert "password" not in response.text


def test_unknown_route_uses_error_envelope():
    with TestClient(create_app()) as client:
        response = client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Recurso não encontrado.",
            "details": None,
        }
    }
