"""Política de senha, hashes Argon2id e tokens de acesso JWT."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: int
    session_version: int


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
    session_version: int = 0,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(seconds=ACCESS_TOKEN_EXPIRES_SECONDS)
    claims: dict[str, object] = {"sub": str(user_id), "iat": issued_at, "exp": expires_at}
    # Omitida na versão inicial: tokens anteriores ao campo continuam válidos.
    if session_version:
        claims["ver"] = session_version
    return jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, secret: str) -> int:
    return decode_access_token_claims(token, secret).user_id


def decode_access_token_claims(token: str, secret: str) -> AccessTokenClaims:
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
        version = payload.get("ver", 0)
        if not isinstance(version, int) or isinstance(version, bool) or version < 0:
            raise InvalidAccessToken("ver inválido")
        return AccessTokenClaims(user_id=int(subject), session_version=version)
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessToken("Token inválido ou expirado.") from exc


def rate_limit_key(secret: str, scope: str, value: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{scope}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_verification_code() -> str:
    """Código numérico de 6 dígitos, fácil de digitar no celular."""

    return f"{secrets.randbelow(1_000_000):06d}"


def verification_code_hash(secret: str, user_id: int, purpose: str, code: str) -> str:
    """Vincula o código ao usuário e à finalidade; o banco guarda só o HMAC."""

    return hmac.new(
        secret.encode("utf-8"),
        f"code:{purpose}:{user_id}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
