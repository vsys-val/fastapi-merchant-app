"""Painel administrativo, eventos e métricas contra PostgreSQL real.

Roda apenas no PostgreSQL efêmero do GitHub Actions, em schema exclusivo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import create_app
from app.models import (
    Base,
    LoginAttempt,
    Product,
    ProductEvent,
    RequestMetric,
    Review,
    ReviewReason,
    User,
)
from app.observability import RequestMetrics
from app.security import create_access_token


SECRET = "test-only-" + "x" * 40


def _ci_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL não foi definido")
    parsed = make_url(database_url)
    if os.getenv("GITHUB_ACTIONS") != "true" or parsed.host not in {"127.0.0.1", "localhost"}:
        pytest.skip("teste destrutivo permitido apenas no PostgreSQL efêmero do GitHub Actions")
    return database_url


@pytest.fixture
def sessions():
    database_url = _ci_database_url()
    admin_engine = create_engine(database_url)
    schema = f"admin_{uuid4().hex}"
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def api(sessions, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc1234")
    application = create_app()

    def database():
        with sessions() as session:
            yield session

    application.dependency_overrides[get_db] = database
    with TestClient(application) as client:
        yield client


def _user(session, email: str, *, created_at: datetime | None = None, verified: bool = True) -> User:
    now = created_at or datetime.now(timezone.utc)
    user = User(
        public_name=email.split("@")[0],
        email=email,
        password_hash="x",
        created_at=now,
        email_verified_at=now if verified else None,
    )
    session.add(user)
    session.flush()
    return user


def _bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, SECRET)}"}


def test_metrics_flush_merges_repeated_minutes(sessions):
    metrics = RequestMetrics()
    at = datetime.now(timezone.utc)
    metrics.record(method="GET", route="/api/v1/products", status_code=200, duration_ms=20, at=at)
    metrics.record(method="GET", route="/api/v1/products", status_code=200, duration_ms=300, at=at)
    with sessions() as session:
        assert metrics.flush(session) == 1
    metrics.record(method="GET", route="/api/v1/products", status_code=200, duration_ms=2000, at=at)
    with sessions() as session:
        metrics.flush(session)
        row = session.scalars(select(RequestMetric)).one()

    assert row.count == 3
    assert row.max_ms == 2000
    assert row.buckets == [1, 0, 0, 0, 1, 0, 0, 1, 0]


def test_flush_applies_retention(sessions):
    old = datetime.now(timezone.utc) - timedelta(days=200)
    with sessions.begin() as session:
        user = _user(session, "antigo@example.com")
        session.add(ProductEvent(name="app_loaded", session_id=str(uuid4()), user_id=user.id, properties={}, created_at=old))
        session.add(RequestMetric(minute=old, method="GET", route="/x", status_class=2, count=1, total_ms=1, max_ms=1, buckets=[1] + [0] * 8))

    metrics = RequestMetrics()
    metrics.record(method="GET", route="/y", status_code=200, duration_ms=1, at=datetime.now(timezone.utc))
    with sessions() as session:
        metrics.flush(session)
        assert session.scalar(select(RequestMetric.route)) == "/y"
        assert session.scalars(select(ProductEvent)).all() == []


def test_events_are_stored_anonymously_or_with_a_valid_user(api, sessions):
    with sessions.begin() as session:
        user = _user(session, "ana@example.com")
    session_id = str(uuid4())

    anonymous = api.post("/api/v1/events", json={"session_id": session_id, "events": [{"name": "app_loaded", "properties": {"commit": "web123"}}]})
    identified = api.post("/api/v1/events", headers=_bearer(user), json={"session_id": session_id, "events": [{"name": "search_performed", "properties": {"results": 2}}]})
    stale = api.post("/api/v1/events", headers={"Authorization": "Bearer invalido"}, json={"session_id": session_id, "events": [{"name": "product_viewed"}]})

    assert (anonymous.status_code, identified.status_code, stale.status_code) == (202, 202, 202)
    with sessions() as session:
        stored = {event.name: event.user_id for event in session.scalars(select(ProductEvent))}
    assert stored == {"app_loaded": None, "search_performed": user.id, "product_viewed": None}


def test_events_are_rate_limited_per_ip(api, sessions, monkeypatch):
    monkeypatch.setattr("app.events.EVENTS_LIMIT", 2)
    body = {"session_id": str(uuid4()), "events": [{"name": "app_loaded"}]}
    statuses = [api.post("/api/v1/events", json=body).status_code for _ in range(3)]
    assert statuses == [202, 202, 429]
    with sessions.begin() as session:
        session.query(LoginAttempt).delete()


def test_overview_reflects_business_usage_and_operations(api, sessions):
    now = datetime.now(timezone.utc)
    with sessions.begin() as session:
        admin = _user(session, "admin@example.com", created_at=now - timedelta(days=20))
        ana = _user(session, "ana@example.com", created_at=now - timedelta(days=10))
        bia = _user(session, "bia@example.com", created_at=now - timedelta(days=9))
        _user(session, "pendente@example.com", verified=False)
        cafe = Product(responsible_id=ana.id, name="Café", brand="Pilão", quantity=Decimal("500"), unit="g", category="food", identity_key="cafe")
        sabao = Product(responsible_id=ana.id, name="Sabão", brand="Omo", quantity=Decimal("1000"), unit="g", category="cleaning", identity_key="sabao")
        session.add_all([cafe, sabao])
        session.flush()
        # Ana avalia no dia seguinte ao cadastro (ativada); Bia não avalia (não ativada).
        review = Review(author_id=ana.id, product_id=cafe.id, repurchase_intent="yes", quality="high", expectation="met", value_for_money="good", comment=None, created_at=ana.created_at + timedelta(days=1))
        review.reasons = [ReviewReason(aspect="taste", perception="positive"), ReviewReason(aspect="price", perception="negative")]
        session.add(review)

        def event(name, user=None, sid="s1", **props):
            session.add(ProductEvent(name=name, session_id=sid, user_id=user.id if user else None, properties=props))

        event("search_performed", ana, results=3, mode="text")
        event("search_performed", ana, results=0, mode="text")
        event("search_performed", None, "s2", results=1, mode="barcode")
        event("search_performed", None, "s2", results=2, mode="text", approximate=True)
        event("product_viewed", ana, product_id=cafe.id, own_review=True)
        event("product_viewed", ana, product_id=cafe.id, own_review=True)
        event("product_viewed", bia, "s3", product_id=cafe.id, own_review=False)
        for step in (1, 2, 3):
            event("review_step_viewed", ana, step=step, editing=False)
        event("review_saved", ana, editing=False)
        event("review_step_viewed", bia, "s3", step=1, editing=False)
        event("product_create_submitted", ana)
        event("product_created", ana)
        event("product_create_submitted", ana)
        event("product_create_conflict", ana)
        event("app_loaded", None, "s2", commit="web123")
        event("client_error", None, "s2", message="TypeError: x is undefined", source="app.js")

    metrics = api.app.state.request_metrics
    metrics.drain()
    for duration, status in ((20, 200), (40, 200), (900, 500), (60, 404)):
        metrics.record(method="GET", route="/api/v1/products", status_code=status, duration_ms=duration, at=now)
    with sessions() as session:
        metrics.flush(session)

    response = api.get("/api/v1/admin/overview?days=30", headers=_bearer(admin))
    assert response.status_code == 200
    data = response.json()

    assert data["system"]["api_commit"] == "abc1234"
    assert data["system"]["database"]["status"] == "available"
    assert data["totals"] == {
        "users": 4, "users_verified": 3, "users_pending": 1, "products_active": 2,
        "products_deleted": 0, "reviews": 1, "reviews_with_comment": 0,
    }
    assert len(data["daily"]) == 30
    assert sum(day["new_users"] for day in data["daily"]) == 4

    product = data["product"]
    # 2 consultas a produto já avaliado / 2 usuários ativos na semana (Ana e Bia).
    assert product["north_star"]["value"] == 1.0
    # A sugestão aproximada conta como busca, mas não como busca com resultado.
    assert product["searches"] == {
        "total": 4, "with_results_pct": 50.0, "barcode_pct": 25.0, "approximate_pct": 25.0,
        "target_with_results_pct": 70,
    }
    assert product["activation"]["cohort"] == 3 and product["activation"]["activated"] == 1
    assert [step["sessions"] for step in product["review_funnel"]["steps"]] == [2, 1, 1, 1]
    assert product["review_funnel"]["abandonment_pct"] == 50.0
    assert product["product_creation"]["conflict_pct"] == 50.0

    catalog = data["catalog"]
    assert catalog["products_without_reviews_pct"] == 50.0
    assert catalog["top_products"][0]["name"] == "Café"
    assert {row["aspect"]: (row["positive"], row["negative"]) for row in catalog["aspects"]} == {"taste": (1, 0), "price": (0, 1)}
    assert catalog["repurchase"] == {"yes": 1, "maybe": 0, "no": 0}

    technical = data["technical"]
    assert technical["requests"] >= 4
    assert technical["error_5xx_pct"] is not None
    route = next(row for row in technical["routes_24h"] if row["route"] == "/api/v1/products")
    assert route["requests"] == 4 and route["error_5xx_pct"] == 25.0 and route["p95_ms"] == 1600

    frontend = data["frontend"]
    assert frontend["versions"][0]["commit"] == "web123"
    assert frontend["top_errors"][0]["message"] == "TypeError: x is undefined"
