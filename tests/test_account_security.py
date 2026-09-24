"""Regras de conta que não dependem de banco: configuração, tokens e códigos."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import auth
from app.database import get_db
from app.errors import ApiError
from app.main import create_app
from app.models import User
from app.schemas import EmailVerificationInput, LoginInput, PasswordResetConfirm
from app.security import (
    InvalidAccessToken,
    create_access_token,
    decode_access_token_claims,
    generate_verification_code,
    verification_code_hash,
)


SECRET = "test-only-" + "x" * 40


@pytest.fixture
def environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", SECRET)
    for name in ("ENVIRONMENT", "EMAIL_DELIVERY"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_log_delivery_is_refused_in_production(environment):
    environment.setenv("ENVIRONMENT", "production")
    environment.setenv("EMAIL_DELIVERY", "log")
    with pytest.raises(RuntimeError, match="EMAIL_DELIVERY"):
        create_app()


def test_verification_is_off_until_email_can_be_delivered(environment):
    application = create_app()
    assert application.state.settings.email_verification_enabled is False
    assert application.state.email_sender is None

    environment.setenv("EMAIL_DELIVERY", "log")
    application = create_app()
    assert application.state.settings.email_verification_enabled is True
    assert application.state.email_sender is not None


@pytest.mark.parametrize("path", ["/api/v1/auth/password-reset", "/api/v1/auth/email-verification/resend"])
def test_email_endpoints_report_unavailable_without_delivery(environment, path):
    application = create_app()
    application.dependency_overrides[get_db] = lambda: SimpleNamespace()
    with TestClient(application) as client:
        response = client.post(path, json={"email": "valerio@example.com"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "email_unavailable"


def test_session_version_is_carried_only_after_a_password_change():
    initial = jwt.decode(create_access_token(7, SECRET), SECRET, algorithms=["HS256"])
    assert "ver" not in initial

    changed = create_access_token(7, SECRET, session_version=2)
    assert decode_access_token_claims(changed, SECRET).session_version == 2


@pytest.mark.parametrize("version", [-1, "1", True, 1.5])
def test_invalid_session_version_is_rejected(version):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": "7", "iat": now, "exp": now.timestamp() + 60, "ver": version},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(InvalidAccessToken):
        decode_access_token_claims(token, SECRET)


def test_verification_codes_are_six_digits_and_bound_to_user_and_purpose():
    codes = {generate_verification_code() for _ in range(200)}
    assert all(len(code) == 6 and code.isdigit() for code in codes)
    assert len(codes) > 150

    base = verification_code_hash(SECRET, 1, "email_verification", "123456")
    assert base != verification_code_hash(SECRET, 2, "email_verification", "123456")
    assert base != verification_code_hash(SECRET, 1, "password_reset", "123456")
    assert "123456" not in base


@pytest.mark.parametrize("code", ["12345", "1234567", "12a456", " 123456"])
def test_code_inputs_must_be_exactly_six_digits(code):
    with pytest.raises(ValidationError):
        EmailVerificationInput(email="valerio@example.com", code=code)


def test_new_password_follows_the_same_policy():
    with pytest.raises(ValidationError):
        PasswordResetConfirm(email="valerio@example.com", code="123456", new_password="curta")
    with pytest.raises(ValidationError):
        PasswordResetConfirm(
            email="valerio@example.com", code="123456", new_password="senhasenhasenha"
        )


def test_unverified_account_is_blocked_only_after_the_password_matches(monkeypatch):
    settings = SimpleNamespace(
        jwt_secret=SimpleNamespace(get_secret_value=lambda: SECRET),
        email_verification_enabled=True,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings)),
        client=SimpleNamespace(host="127.0.0.1"),
    )
    session = Mock()
    session.scalar.return_value = User(
        id=7,
        public_name="Valério",
        email="valerio@example.com",
        password_hash="stored",
        email_verified_at=None,
        session_version=0,
    )
    monkeypatch.setattr(auth, "consume_attempt", lambda *args, **kwargs: 1)
    monkeypatch.setattr(auth, "active_attempt_count", lambda *args, **kwargs: 0)
    monkeypatch.setattr(auth, "dummy_password_hash", lambda: "dummy")

    monkeypatch.setattr(auth, "verify_password", lambda password, stored: False)
    with pytest.raises(ApiError) as wrong_password:
        auth.login(LoginInput(email="valerio@example.com", password="errada"), request, session)
    assert wrong_password.value.code == "invalid_credentials"

    monkeypatch.setattr(auth, "verify_password", lambda password, stored: True)
    with pytest.raises(ApiError) as pending:
        auth.login(LoginInput(email="valerio@example.com", password="correta"), request, session)
    assert pending.value.status_code == 403
    assert pending.value.code == "email_not_verified"
