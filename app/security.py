"""Política de senha, hashes Argon2id e tokens de acesso JWT."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash


JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_SECONDS = 86400

# Lista local intencionalmente pequena no MVP. Pode ser ampliada sem mudar o
# contrato. A comparação não remove espaços, pois eles fazem parte da senha.
COMMON_PASSWORDS = frozenset(
    {
        "123456789012345",
        "1234567890123456",
        "adminadminadmin",
        "administrador123",
        "iloveyouiloveyou",
        "passwordpassword",
        "qwertyqwertyqwerty",
        "senha123456789",
        "senha1234567890",
        "senhasenhasenha",
    }
)

_password_hash = PasswordHash.recommended()
_dummy_hash: str | None = None


class InvalidAccessToken(ValueError):
    pass


def validate_password_policy(password: str) -> str:
    if len(password) < 15:
        raise ValueError("A senha deve ter no mínimo 15 caracteres.")
    if len(password) > 128:
        raise ValueError("A senha deve ter no máximo 128 caracteres.")
    if password.casefold() in COMMON_PASSWORDS:
        raise ValueError("Escolha uma senha menos comum.")
    return password


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def dummy_password_hash() -> str:
    """Hash usado para aproximar o custo do login de uma conta inexistente."""

    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("dummy-password-never-used")
    return _dummy_hash


def create_access_token(
    user_id: int,
    secret: str,
    *,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(seconds=ACCESS_TOKEN_EXPIRES_SECONDS)
    return jwt.encode(
        {"sub": str(user_id), "iat": issued_at, "exp": expires_at},
        secret,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str, secret: str) -> int:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
        subject = payload["sub"]
        if not isinstance(subject, str) or not subject.isdecimal() or int(subject) <= 0:
            raise InvalidAccessToken("sub inválido")
        return int(subject)
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessToken("Token inválido ou expirado.") from exc


def rate_limit_key(secret: str, scope: str, value: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{scope}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
