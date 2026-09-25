"""Regras do painel que não dependem de banco: métricas, eventos e acesso."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth import get_current_user
from app.config import Settings
from app.database import get_db
from app.events import EventBatch
from app.main import create_app
from app.models import User
from app.observability import (
    ABOVE_LAST_BUCKET_MS,
    LATENCY_BUCKETS_MS,
    RequestMetrics,
    bucket_index,
    percentile_from_buckets,
)


SESSION = "0b6c3a5e-6d1f-4f0e-9d7a-1c2b3d4e5f60"


@pytest.fixture
def application(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    monkeypatch.setenv("ADMIN_EMAILS", " Admin@Example.com ,admin@example.com")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    return app


def _user(email: str) -> User:
    return User(id=1, public_name="Pessoa", email=email, password_hash="x", email_verified_at=datetime.now(timezone.utc), session_version=0)


def test_buckets_and_percentiles():
    assert bucket_index(10) == 0
    assert bucket_index(25) == 0
    assert bucket_index(26) == 1
    assert bucket_index(5000) == len(LATENCY_BUCKETS_MS)

    assert percentile_from_buckets([0] * 9, 0.95) is None
    assert percentile_from_buckets([90, 5, 5, 0, 0, 0, 0, 0, 0], 0.95) == 50
    assert percentile_from_buckets([0, 0, 0, 0, 0, 0, 0, 0, 10], 0.95) == ABOVE_LAST_BUCKET_MS


def test_request_metrics_aggregate_by_minute_route_and_status_class():
    metrics = RequestMetrics()
    at = datetime(2026, 9, 24, 12, 30, 45, tzinfo=timezone.utc)
    for duration in (10, 30, 900):
        metrics.record(method="GET", route="/api/v1/products", status_code=200, duration_ms=duration, at=at)
    metrics.record(method="GET", route="/api/v1/products", status_code=503, duration_ms=5, at=at)

    pending = metrics.drain()
    ok = pending[(at.replace(second=0), "GET", "/api/v1/products", 2)]
    assert (ok.count, ok.max_ms) == (3, 900)
    assert ok.buckets[0] == 1 and ok.buckets[1] == 1 and ok.buckets[6] == 1
    assert pending[(at.replace(second=0), "GET", "/api/v1/products", 5)].count == 1
    assert metrics.drain() == {}

    metrics.restore(pending)
    metrics.restore(pending)
    assert metrics.drain()[(at.replace(second=0), "GET", "/api/v1/products", 2)].count == 6


def test_middleware_records_route_templates_and_ignores_health(application, monkeypatch):
    monkeypatch.setattr("app.routes.get_product_detail", lambda *_args: (_ for _ in ()).throw(RuntimeError("boom")))
    with TestClient(application, raise_server_exceptions=False) as client:
        metrics = application.state.request_metrics
        client.get("/api/v1/products/42")
        client.get("/api/v1/products/43")
        client.get("/rota-inexistente")
        client.get("/health")
        pending = metrics.drain()

    routes = {(key[2], key[3]): value.count for key, value in pending.items()}
    assert routes[("/api/v1/products/{product_id}", 5)] == 2
    assert routes[("<não encontrada>", 4)] == 1
    assert not any(route == "/health" for route, _ in routes)


def test_admin_emails_are_normalized():
    settings = Settings(
        database_url="postgresql+psycopg://test:password@localhost/test_db",
        jwt_secret="test-only-" + "x" * 40,
        admin_emails=" Admin@Example.com , outra@example.com,admin@example.com ",
    )
    assert settings.admin_email_set == {"admin@example.com", "outra@example.com"}


def test_overview_requires_an_admin(application):
    application.dependency_overrides[get_current_user] = lambda: _user("comum@example.com")
    with TestClient(application) as client:
        forbidden = client.get("/api/v1/admin/overview")
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "admin_required"

    with TestClient(application) as client:
        application.dependency_overrides.pop(get_current_user)
        assert client.get("/api/v1/admin/overview").status_code == 401


def test_users_me_reports_admin_flag(application):
    application.dependency_overrides[get_current_user] = lambda: _user("admin@example.com")
    with TestClient(application) as client:
        assert client.get("/api/v1/users/me").json()["is_admin"] is True
    application.dependency_overrides[get_current_user] = lambda: _user("comum@example.com")
    with TestClient(application) as client:
        assert client.get("/api/v1/users/me").json()["is_admin"] is False


def test_event_batches_only_accept_known_names_and_small_scalars():
    batch = EventBatch(session_id=SESSION, events=[{"name": "search_performed", "properties": {"results": 3, "mode": "text"}}])
    assert batch.events[0].properties == {"results": 3, "mode": "text"}

    scan = EventBatch(session_id=SESSION, events=[{"name": "barcode_scan", "properties": {"outcome": "detected", "engine": None}}])
    assert scan.events[0].properties == {"outcome": "detected", "engine": None}

    long_text = EventBatch(session_id=SESSION, events=[{"name": "client_error", "properties": {"message": "x" * 500}}])
    assert len(long_text.events[0].properties["message"]) == 200

    for invalid in (
        {"session_id": SESSION, "events": [{"name": "evento_desconhecido"}]},
        {"session_id": SESSION, "events": [{"name": "app_loaded", "properties": {"lista": [1, 2]}}]},
        {"session_id": SESSION, "events": [{"name": "app_loaded", "properties": {f"p{i}": i for i in range(9)}}]},
        {"session_id": SESSION, "events": [{"name": "app_loaded", "properties": {"com espaço": 1}}]},
        {"session_id": "nao-e-uuid", "events": [{"name": "app_loaded"}]},
        {"session_id": SESSION, "events": [{"name": "app_loaded"}] * 21},
    ):
        with pytest.raises(ValidationError):
            EventBatch(**invalid)
