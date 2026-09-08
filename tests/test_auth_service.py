from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError

from app import auth
from app.errors import ApiError
from app.models import User
from app.schemas import LoginInput, UserCreate


SECRET = "test-only-" + "x" * 40


def request_stub(ip="127.0.0.1"):
    settings = SimpleNamespace(jwt_secret=SimpleNamespace(get_secret_value=lambda: SECRET))
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)), client=SimpleNamespace(host=ip))


def user_stub(user_id=7):
    return User(
        id=user_id,
        public_name="Valério",
        email="valerio@example.com",
        password_hash="stored-hash",
    )


def test_create_user_persists_only_hash_and_returns_public_fields(monkeypatch):
    session = Mock()
    session.scalar.return_value = None
    session.refresh.side_effect = lambda user: setattr(user, "id", 7)
    monkeypatch.setattr(auth, "hash_password", lambda password: "argon2id-hash")
    payload = UserCreate(
        email="valerio@example.com",
        name="Valério",
        password="uma frase secreta longa",
    )

    result = auth.create_user(payload, session)

    stored = session.add.call_args.args[0]
    assert stored.password_hash == "argon2id-hash"
    assert result.model_dump(mode="json") == {
        "id": 7,
        "name": "Valério",
        "email": "valerio@example.com",
    }
    session.commit.assert_called_once()


def test_create_user_reports_duplicate_found_before_insert():
    session = Mock()
    session.scalar.return_value = 7
    payload = UserCreate(
        email="valerio@example.com",
        name="Outro nome",
        password="outra frase secreta longa",
    )
    with pytest.raises(ApiError) as caught:
        auth.create_user(payload, session)
    assert caught.value.status_code == 409
    assert caught.value.code == "email_already_registered"
    session.add.assert_not_called()


def test_create_user_concurrent_duplicate_rolls_back(monkeypatch):
    session = Mock()
    session.scalar.return_value = None
    session.commit.side_effect = IntegrityError("insert", {}, Exception("unique"))
    monkeypatch.setattr(auth, "hash_password", lambda password: "argon2id-hash")
    payload = UserCreate(
        email="valerio@example.com",
        name="Valério",
        password="uma frase secreta longa",
    )
    with pytest.raises(ApiError) as caught:
        auth.create_user(payload, session)
    assert caught.value.status_code == 409
    session.rollback.assert_called_once()


def test_login_success_resets_account_counter_and_returns_token(monkeypatch):
    session = Mock()
    session.scalar.return_value = user_stub()
    monkeypatch.setattr(auth, "consume_attempt", lambda *args, **kwargs: 1)
    monkeypatch.setattr(auth, "active_attempt_count", lambda *args, **kwargs: 0)
    monkeypatch.setattr(auth, "verify_password", lambda password, stored: True)
    reset = Mock()
    monkeypatch.setattr(auth, "reset_attempts", reset)
    monkeypatch.setattr(auth, "create_access_token", lambda user_id, secret: "valid-token")

    result = auth.login(
        LoginInput(email="valerio@example.com", password="senha correta"),
        request_stub(),
        session,
    )
    assert result.access_token == "valid-token"
    assert result.expires_in == 86400
    reset.assert_called_once()
    assert session.commit.call_count == 2


@pytest.mark.parametrize("existing_user", [None, user_stub()])
def test_login_failure_is_generic_for_unknown_email_and_wrong_password(
    monkeypatch, existing_user
):
    session = Mock()
    session.scalar.return_value = existing_user
    counts = iter([1, 1])
    monkeypatch.setattr(auth, "consume_attempt", lambda *args, **kwargs: next(counts))
    monkeypatch.setattr(auth, "active_attempt_count", lambda *args, **kwargs: 0)
    monkeypatch.setattr(auth, "verify_password", lambda password, stored: False)
    monkeypatch.setattr(auth, "dummy_password_hash", lambda: "dummy-hash")

    with pytest.raises(ApiError) as caught:
        auth.login(
            LoginInput(email="unknown@example.com", password="senha errada"),
            request_stub(),
            session,
        )
    assert caught.value.status_code == 401
    assert caught.value.code == "invalid_credentials"
    assert caught.value.message == "E-mail ou senha inválidos."


def test_login_limits_ip_before_reading_account(monkeypatch):
    session = Mock()
    monkeypatch.setattr(auth, "consume_attempt", lambda *args, **kwargs: 21)
    with pytest.raises(ApiError) as caught:
        auth.login(
            LoginInput(email="valerio@example.com", password="qualquer"),
            request_stub(),
            session,
        )
    assert caught.value.status_code == 429
    session.scalar.assert_not_called()


def test_login_limits_account_after_five_failures(monkeypatch):
    session = Mock()
    monkeypatch.setattr(auth, "consume_attempt", lambda *args, **kwargs: 1)
    monkeypatch.setattr(auth, "active_attempt_count", lambda *args, **kwargs: 5)
    verify = Mock()
    monkeypatch.setattr(auth, "verify_password", verify)
    with pytest.raises(ApiError) as caught:
        auth.login(
            LoginInput(email="valerio@example.com", password="qualquer"),
            request_stub(),
            session,
        )
    assert caught.value.status_code == 429
    verify.assert_not_called()


def test_current_user_accepts_valid_token_and_rejects_missing_user(monkeypatch):
    session = Mock()
    user = user_stub(42)
    session.get.return_value = user
    monkeypatch.setattr(auth, "decode_access_token", lambda token, secret: 42)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    assert auth.get_current_user(request_stub(), credentials, session) is user

    session.get.return_value = None
    with pytest.raises(ApiError) as caught:
        auth.get_current_user(request_stub(), credentials, session)
    assert caught.value.status_code == 401
