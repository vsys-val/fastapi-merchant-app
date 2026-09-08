"""Casos de uso de cadastro, login e autenticação Bearer."""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import User
from app.rate_limit import (
    ACCOUNT_LIMIT,
    ACCOUNT_WINDOW,
    IP_LIMIT,
    IP_WINDOW,
    active_attempt_count,
    consume_attempt,
    reset_attempts,
)
from app.schemas import LoginInput, TokenResponse, UserCreate, UserPublic
from app.security import (
    create_access_token,
    decode_access_token,
    dummy_password_hash,
    hash_password,
    rate_limit_key,
    verify_password,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="JWT emitido por POST /api/v1/auth/login.",
)


def _authentication_error() -> ApiError:
    return ApiError(
        status_code=401,
        code="invalid_authentication",
        message="Autenticação ausente, inválida ou expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _public_user(user: User) -> UserPublic:
    return UserPublic(id=user.id, name=user.public_name, email=user.email)


def create_user(payload: UserCreate, session: Session) -> UserPublic:
    if session.scalar(select(User.id).where(User.email == str(payload.email))) is not None:
        raise ApiError(409, "email_already_registered", "Este e-mail já está cadastrado.")

    user = User(
        public_name=payload.name,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ApiError(409, "email_already_registered", "Este e-mail já está cadastrado.") from exc
    session.refresh(user)
    return _public_user(user)


def login(payload: LoginInput, request: Request, session: Session) -> TokenResponse:
    settings = request.app.state.settings
    secret = settings.jwt_secret.get_secret_value()
    client_ip = request.client.host if request.client else "unknown"
    ip_key = rate_limit_key(secret, "ip", client_ip)
    account_key = rate_limit_key(secret, "account", str(payload.email))

    ip_count = consume_attempt(session, scope="ip", key_hash=ip_key, window=IP_WINDOW)
    session.commit()
    if ip_count > IP_LIMIT:
        raise ApiError(429, "login_rate_limited", "Muitas tentativas de login. Tente novamente mais tarde.")

    if active_attempt_count(
        session, scope="account", key_hash=account_key, window=ACCOUNT_WINDOW
    ) >= ACCOUNT_LIMIT:
        raise ApiError(429, "login_rate_limited", "Muitas tentativas de login. Tente novamente mais tarde.")

    user = session.scalar(select(User).where(User.email == str(payload.email)))
    candidate_hash = user.password_hash if user is not None else dummy_password_hash()
    password_matches = verify_password(payload.password, candidate_hash)

    if user is None or not password_matches:
        account_count = consume_attempt(
            session, scope="account", key_hash=account_key, window=ACCOUNT_WINDOW
        )
        session.commit()
        if account_count > ACCOUNT_LIMIT:
            raise ApiError(429, "login_rate_limited", "Muitas tentativas de login. Tente novamente mais tarde.")
        raise ApiError(401, "invalid_credentials", "E-mail ou senha inválidos.", headers={"WWW-Authenticate": "Bearer"})

    reset_attempts(session, scope="account", key_hash=account_key)
    session.commit()
    return TokenResponse(access_token=create_access_token(user.id, secret))


def _resolve_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials,
    session: Session,
) -> User:
    if credentials.scheme.casefold() != "bearer":
        raise _authentication_error()
    try:
        user_id = decode_access_token(
            credentials.credentials,
            request.app.state.settings.jwt_secret.get_secret_value(),
        )
    except ValueError:
        raise _authentication_error() from None
    user = session.get(User, user_id)
    if user is None:
        raise _authentication_error()
    return user


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        if request.headers.get("Authorization"):
            raise _authentication_error()
        return None
    return _resolve_authenticated_user(request, credentials, session)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _authentication_error()
    return _resolve_authenticated_user(request, credentials, session)


def current_user_response(user: User = Depends(get_current_user)) -> UserPublic:
    return _public_user(user)
