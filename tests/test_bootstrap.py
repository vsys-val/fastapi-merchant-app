import traceback

import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in ("ENVIRONMENT", "DATABASE_URL", "MIGRATION_DATABASE_URL", "JWT_SECRET"):
        monkeypatch.delenv(name, raising=False)


def configure(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)


def test_application_serves_documentation_without_exposing_configuration(monkeypatch):
    configure(monkeypatch)
    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert schema.json()["info"]["title"] == "FastAPI Merchant App"
        assert "test-only-" not in schema.text
        assert "password" not in schema.text


def test_missing_settings_prevent_startup():
    with pytest.raises(RuntimeError, match="DATABASE_URL, JWT_SECRET"):
        create_app()


@pytest.mark.parametrize("field,value", [
    ("JWT_SECRET", "short-private-key"),
    ("DATABASE_URL", "invalid-private-database-url"),
    ("DATABASE_URL", "sqlite:///private.db"),
    ("DATABASE_URL", "postgresql+psycopg://user:private-password@localhost"),
])
def test_invalid_settings_fail_without_secret_in_traceback(monkeypatch, field, value):
    configure(monkeypatch)
    monkeypatch.setenv(field, value)
    with pytest.raises(RuntimeError) as error:
        create_app()
    rendered = "".join(traceback.format_exception(error.value))
    assert field in str(error.value)
    assert value not in rendered
    assert "private-password" not in rendered


def test_environment_overrides_dotenv_and_secrets_are_masked(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://local:password@localhost/test_db\n"
        "JWT_SECRET=" + "local-only-" + "y" * 40 + "\nENVIRONMENT=development\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ENVIRONMENT", "test")
    settings = load_settings()
    assert settings.environment == "test"
    assert "local-only-" not in repr(settings)
    assert "password" not in repr(settings)


def test_migration_url_defaults_to_runtime_url(monkeypatch):
    configure(monkeypatch)
    settings = load_settings()
    assert settings.alembic_database_url == settings.database_url


def test_migration_url_can_use_a_separate_supabase_connection(monkeypatch):
    configure(monkeypatch)
    direct_url = "postgresql+psycopg://postgres:password@db.project.supabase.co/postgres"
    monkeypatch.setenv("MIGRATION_DATABASE_URL", direct_url)
    settings = load_settings()
    assert settings.alembic_database_url.get_secret_value() == direct_url
