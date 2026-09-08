from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import create_app
from app.models import Base


def _configure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:password@localhost/test_db",
    )
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)


def test_health_confirms_application_and_database_are_available(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
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
        response = client.get("/health")
        versioned_response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "available"}
    assert versioned_response.status_code == 404
    session.close()
    Base.metadata.drop_all(engine)


def test_health_returns_safe_503_when_database_is_unavailable(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)

    class UnavailableSession:
        def execute(self, _statement):
            raise SQLAlchemyError("private database address and SQL details")

    application = create_app()
    application.dependency_overrides[get_db] = UnavailableSession

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "O banco de dados está temporariamente indisponível.",
            "details": None,
        }
    }
    assert "private database" not in response.text
    assert "SQL" not in response.text


def test_unexpected_errors_return_a_safe_generic_envelope(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    application = create_app()

    @application.get("/explode", include_in_schema=False)
    def explode():
        raise RuntimeError("private-password SELECT * FROM usuarios")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/explode")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Ocorreu um erro interno inesperado.",
            "details": None,
        }
    }
    assert "private-password" not in response.text
    assert "usuarios" not in response.text


def test_openapi_describes_operational_and_bearer_auth_contract(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    schema = create_app().openapi()

    assert schema["info"]["version"] == "1.0.0"
    assert {tag["name"] for tag in schema["tags"]} == {"API", "Operational"}
    assert schema["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "description": "JWT emitido por POST /api/v1/auth/login.",
        "scheme": "bearer",
    }
    optional_security = [{"BearerAuth": []}, {}]
    assert schema["paths"]["/api/v1/products"]["get"]["security"] == optional_security
    assert (
        schema["paths"]["/api/v1/products/{product_id}"]["get"]["security"]
        == optional_security
    )
    assert (
        schema["paths"]["/api/v1/products/{product_id}/reviews"]["get"]["security"]
        == optional_security
    )
    assert schema["paths"]["/api/v1/products"]["post"]["security"] == [
        {"BearerAuth": []}
    ]
    assert schema["paths"]["/api/v1/users/me"]["get"]["security"] == [
        {"BearerAuth": []}
    ]
    assert "security" not in schema["paths"]["/health"]["get"]
    assert schema["paths"]["/health"]["get"]["tags"] == ["Operational"]
    assert schema["paths"]["/health"]["get"]["responses"]["503"] == {
        "description": "Banco de dados indisponível.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
            }
        },
    }
    assert "500" in schema["paths"]["/api/v1/products"]["get"]["responses"]
