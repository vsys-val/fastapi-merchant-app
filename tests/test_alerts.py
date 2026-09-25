"""Alertas: segredo do endpoint e decisões do workflow, sem banco."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.database import get_db
from app.main import create_app

TOKEN = "alertas-" + "x" * 40
spec = importlib.util.spec_from_file_location("check_alerts", Path(__file__).parents[1] / "scripts" / "check_alerts.py")
check_alerts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_alerts)


def _settings(**changes):
    values = {"database_url": "postgresql+psycopg://test:password@localhost/test_db", "jwt_secret": "test-only-" + "x" * 40}
    values.update(changes)
    return Settings(**values)


def _client(monkeypatch, tmp_path, token: str | None):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    if token:
        monkeypatch.setenv("ALERTS_TOKEN", token)
    monkeypatch.setattr("app.routes.evaluate_alerts", lambda _session: {"status": "ok", "checks": []})
    application = create_app()
    application.dependency_overrides[get_db] = lambda: SimpleNamespace()
    return TestClient(application)


def test_alerts_token_is_optional_but_must_be_long():
    assert _settings().alerts_token is None
    assert _settings(alerts_token="").alerts_token is None
    with pytest.raises(ValidationError):
        _settings(alerts_token="curto")


def test_endpoint_does_not_exist_without_token(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path, None) as client:
        assert client.get("/api/v1/internal/alerts", headers={"X-Alerts-Token": TOKEN}).status_code == 404


def test_endpoint_requires_the_shared_secret(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path, TOKEN) as client:
        assert client.get("/api/v1/internal/alerts").status_code == 401
        assert client.get("/api/v1/internal/alerts", headers={"X-Alerts-Token": TOKEN + "x"}).status_code == 401
        response = client.get("/api/v1/internal/alerts", headers={"X-Alerts-Token": TOKEN})
        assert (response.status_code, response.json()["status"]) == (200, "ok")
        assert "/api/v1/internal/alerts" not in client.get("/openapi.json").json()["paths"]


@pytest.mark.parametrize(
    ("status", "open_issue", "action"),
    [("alert", None, "create"), ("alert", {"number": 3}, "update"), ("ok", {"number": 3}, "close"), ("ok", None, "none")],
)
def test_workflow_keeps_a_single_alert_issue(status, open_issue, action):
    assert check_alerts.decide({"status": status, "checks": []}, open_issue) == action


def test_issue_body_lists_every_check():
    body = check_alerts.render_body({
        "status": "alert",
        "evaluated_at": "2026-09-25T15:00:00+00:00",
        "checks": [
            {"label": "Erros 5xx", "ok": False, "threshold": "< 5%", "detail": "3 de 40 requisições."},
            {"label": "Banco de dados", "ok": True, "threshold": "disponível", "detail": "Respondendo."},
        ],
    })
    assert "| Erros 5xx | ❌ violado | < 5% | 3 de 40 requisições. |" in body
    assert "| Banco de dados | ✅ ok |" in body


def test_unreachable_api_becomes_an_alert(monkeypatch):
    def fail(*_args, **_kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr(check_alerts, "urlopen", fail)
    result = check_alerts.fetch_alerts(TOKEN, attempts=2, wait_seconds=0)
    assert result["status"] == "alert"
    assert result["checks"][0]["key"] == "api"
    assert "2 tentativas" in result["checks"][0]["detail"]


def test_rejected_token_fails_the_workflow(monkeypatch):
    def reject(*_args, **_kwargs):
        raise HTTPError("url", 401, "Unauthorized", {}, None)

    monkeypatch.setattr(check_alerts, "urlopen", reject)
    with pytest.raises(SystemExit, match="ALERTS_TOKEN"):
        check_alerts.fetch_alerts(TOKEN, attempts=1, wait_seconds=0)


def test_missing_secret_skips_quietly(monkeypatch, capsys):
    monkeypatch.delenv("ALERTS_TOKEN", raising=False)
    assert check_alerts.main() == 0
    assert "alertas desligados" in capsys.readouterr().out
