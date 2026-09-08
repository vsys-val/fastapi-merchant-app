from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.security import (
    ACCESS_TOKEN_EXPIRES_SECONDS,
    InvalidAccessToken,
    create_access_token,
    decode_access_token,
    hash_password,
    rate_limit_key,
    validate_password_policy,
    verify_password,
)


SECRET = "test-only-" + "s" * 40


def test_argon2id_hash_is_salted_and_verifiable():
    password = "frase secreta longa"
    first = hash_password(password)
    second = hash_password(password)

    assert first.startswith("$argon2id$")
    assert first != second
    assert password not in first
    assert verify_password(password, first)
    assert not verify_password("senha completamente errada", first)


@pytest.mark.parametrize("size", [15, 128])
def test_password_policy_accepts_boundaries_and_preserves_spaces(size):
    password = " " + "x" * (size - 2) + " "
    assert validate_password_policy(password) == password


@pytest.mark.parametrize("password", ["x" * 14, "x" * 129, "senha123456789"])
def test_password_policy_rejects_invalid_or_common_values(password):
    with pytest.raises(ValueError):
        validate_password_policy(password)


def test_jwt_has_only_required_claims_and_expires_in_24_hours():
    now = datetime.now(timezone.utc)
    token = create_access_token(42, SECRET, now=now)
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])

    assert set(payload) == {"sub", "iat", "exp"}
    assert payload["sub"] == "42"
    assert payload["exp"] - payload["iat"] == ACCESS_TOKEN_EXPIRES_SECONDS
    assert decode_access_token(token, SECRET) == 42


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": "1", "iat": datetime.now(timezone.utc)},
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        {"iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        {"sub": "invalid", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
    ],
)
def test_jwt_rejects_missing_or_invalid_claims(payload):
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    with pytest.raises(InvalidAccessToken):
        decode_access_token(token, SECRET)


def test_jwt_rejects_expired_altered_and_wrong_algorithm_tokens():
    past = datetime.now(timezone.utc) - timedelta(days=2)
    expired = create_access_token(1, SECRET, now=past)
    altered = create_access_token(1, SECRET) + "x"
    wrong_algorithm = jwt.encode(
        {
            "sub": "1",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        SECRET,
        algorithm="HS384",
    )
    for token in (expired, altered, wrong_algorithm):
        with pytest.raises(InvalidAccessToken):
            decode_access_token(token, SECRET)


def test_rate_limit_keys_are_scoped_and_do_not_reveal_input():
    email = "private@example.com"
    account_key = rate_limit_key(SECRET, "account", email)
    ip_key = rate_limit_key(SECRET, "ip", email)
    assert len(account_key) == 64
    assert email not in account_key
    assert account_key != ip_key
