"""Fluxos de conta via HTTP contra PostgreSQL real.

Cobrem confirmação de e-mail, recuperação de senha e limites por IP, que
dependem de UPSERT, bloqueios e restrições do PostgreSQL. Como os testes de
concorrência, rodam apenas no PostgreSQL efêmero do GitHub Actions, em um
schema exclusivo removido ao final.
"""

from __future__ import annotations

from datetime import timedelta
import os
import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.email import EmailMessage
from app.main import create_app
from app.models import Base, LoginAttempt, User, VerificationCode


PASSWORD = "frase secreta exclusiva 2026"
NEW_PASSWORD = "outra frase secreta bem longa"


def _ci_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL não foi definido")
    parsed = make_url(database_url)
    if os.getenv("GITHUB_ACTIONS") != "true" or parsed.host not in {"127.0.0.1", "localhost"}:
        pytest.skip("teste destrutivo permitido apenas no PostgreSQL efêmero do GitHub Actions")
    return database_url


class Outbox:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)

    def last_code(self) -> str:
        match = re.search(r"\b(\d{6})\b", self.messages[-1].body)
        assert match is not None
        return match.group(1)


@pytest.fixture(scope="module")
def sessions():
    database_url = _ci_database_url()
    admin_engine = create_engine(database_url)
    schema = f"accounts_{uuid4().hex}"
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
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    monkeypatch.setenv("EMAIL_DELIVERY", "log")
    with sessions.begin() as session:
        session.execute(delete(LoginAttempt))

    application = create_app()
    outbox = Outbox()
    application.state.email_sender = outbox

    def database():
        with sessions() as session:
            yield session

    application.dependency_overrides[get_db] = database
    with TestClient(application) as client:
        client.outbox = outbox
        yield client


def _email() -> str:
    return f"pessoa-{uuid4().hex[:10]}@example.com"


def _register(api, email: str, password: str = PASSWORD):
    return api.post("/api/v1/users", json={"email": email, "name": "Pessoa", "password": password})


def _login(api, email: str, password: str = PASSWORD):
    return api.post("/api/v1/auth/login", json={"email": email, "password": password})


def _verify(api, email: str, code: str):
    return api.post("/api/v1/auth/email-verification", json={"email": email, "code": code})


def _shift(sessions, email: str, **columns: timedelta) -> None:
    """Move instantes para o passado, simulando a passagem do tempo."""

    with sessions.begin() as session:
        user = session.query(User).filter_by(email=email).one()
        if "created_at" in columns:
            user.created_at -= columns["created_at"]
        for name in ("expires_at", "sent_at"):
            if name in columns:
                session.execute(
                    update(VerificationCode)
                    .where(VerificationCode.user_id == user.id)
                    .values({name: getattr(VerificationCode, name) - columns[name]})
                )


def test_new_account_must_confirm_email_before_login(api):
    email = _email()

    created = _register(api, email)
    assert created.status_code == 201
    assert created.json()["email_verified"] is False
    assert len(api.outbox.messages) == 1
    assert api.outbox.messages[0].to == email

    blocked = _login(api, email)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "email_not_verified"

    wrong = _verify(api, email, "000000" if api.outbox.last_code() != "000000" else "111111")
    assert wrong.status_code == 400
    assert wrong.json()["error"]["code"] == "invalid_verification_code"

    confirmed = _verify(api, email, api.outbox.last_code())
    assert confirmed.status_code == 200
    token = confirmed.json()["access_token"]
    me = api.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email_verified"] is True
    assert _login(api, email).status_code == 200

    reused = _verify(api, email, api.outbox.last_code())
    assert reused.status_code == 400


def test_code_is_invalidated_after_five_wrong_attempts(api):
    email = _email()
    _register(api, email)
    code = api.outbox.last_code()
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"

    for _ in range(5):
        assert _verify(api, email, wrong).status_code == 400
    assert _verify(api, email, code).status_code == 400


def test_expired_code_is_rejected(api, sessions):
    email = _email()
    _register(api, email)
    _shift(sessions, email, expires_at=timedelta(minutes=16))

    assert _verify(api, email, api.outbox.last_code()).status_code == 400


def test_resend_respects_cooldown_and_replaces_the_code(api, sessions):
    email = _email()
    _register(api, email)
    first_code = api.outbox.last_code()

    too_soon = api.post("/api/v1/auth/email-verification/resend", json={"email": email})
    assert too_soon.status_code == 202
    assert len(api.outbox.messages) == 1

    _shift(sessions, email, sent_at=timedelta(seconds=61))
    api.post("/api/v1/auth/email-verification/resend", json={"email": email})
    assert len(api.outbox.messages) == 2
    second_code = api.outbox.last_code()

    if second_code != first_code:
        assert _verify(api, email, first_code).status_code == 400
    assert _verify(api, email, second_code).status_code == 200


def test_unknown_email_gets_the_same_response_without_email(api):
    for path in ("/api/v1/auth/email-verification/resend", "/api/v1/auth/password-reset"):
        response = api.post(path, json={"email": _email()})
        assert response.status_code == 202
    assert api.outbox.messages == []


def test_pending_account_holds_the_email_for_24_hours(api, sessions):
    email = _email()
    first = _register(api, email)

    assert _register(api, email, NEW_PASSWORD).status_code == 409

    _shift(sessions, email, created_at=timedelta(hours=25))
    replaced = _register(api, email, NEW_PASSWORD)
    assert replaced.status_code == 201
    assert replaced.json()["id"] != first.json()["id"]
    assert _verify(api, email, api.outbox.last_code()).status_code == 200
    assert _login(api, email, NEW_PASSWORD).status_code == 200


def test_password_reset_changes_password_and_ends_old_sessions(api):
    email = _email()
    _register(api, email)
    old_token = _verify(api, email, api.outbox.last_code()).json()["access_token"]

    assert api.post("/api/v1/auth/password-reset", json={"email": email}).status_code == 202
    code = api.outbox.last_code()
    assert "redefinir" in api.outbox.messages[-1].subject

    wrong = api.post(
        "/api/v1/auth/password-reset/confirm",
        json={"email": email, "code": f"{(int(code) + 1) % 1_000_000:06d}", "new_password": NEW_PASSWORD},
    )
    assert wrong.status_code == 400

    done = api.post(
        "/api/v1/auth/password-reset/confirm",
        json={"email": email, "code": code, "new_password": NEW_PASSWORD},
    )
    assert done.status_code == 204

    stale = api.get("/api/v1/users/me", headers={"Authorization": f"Bearer {old_token}"})
    assert stale.status_code == 401
    assert _login(api, email).status_code == 401
    fresh = _login(api, email, NEW_PASSWORD)
    assert fresh.status_code == 200
    me = api.get("/api/v1/users/me", headers={"Authorization": f"Bearer {fresh.json()['access_token']}"})
    assert me.status_code == 200


def test_owner_recovers_an_email_registered_by_someone_else(api):
    email = _email()
    _register(api, email, "senha escolhida por um invasor")

    api.post("/api/v1/auth/password-reset", json={"email": email})
    api.post(
        "/api/v1/auth/password-reset/confirm",
        json={"email": email, "code": api.outbox.last_code(), "new_password": NEW_PASSWORD},
    )

    assert _login(api, email, "senha escolhida por um invasor").status_code == 401
    assert _login(api, email, NEW_PASSWORD).status_code == 200


def test_registration_is_limited_per_ip(api):
    statuses = [_register(api, _email()).status_code for _ in range(11)]

    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429
    assert api.post("/api/v1/users", json={
        "email": _email(), "name": "Pessoa", "password": PASSWORD,
    }).json()["error"]["code"] == "too_many_requests"
