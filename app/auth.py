"""Casos de uso de cadastro, login e autenticação Bearer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.email import EmailMessage, password_reset_email, verification_email
from app.errors import ApiError
from app.models import User
from app.rate_limit import (
    ACCOUNT_LIMIT,
    ACCOUNT_WINDOW,
    CODE_LIMIT,
    CODE_WINDOW,
    EMAIL_LIMIT,
    EMAIL_WINDOW,
    IP_LIMIT,
    IP_WINDOW,
    REGISTER_LIMIT,
    REGISTER_WINDOW,
    active_attempt_count,
    consume_attempt,
    reset_attempts,
)
from app.schemas import (
    EmailInput,
    EmailVerificationInput,
    LoginInput,
    PasswordResetConfirm,
    TokenResponse,
    UserCreate,
    UserPublic,
)
from app.security import (
    create_access_token,
    decode_access_token_claims,
    dummy_password_hash,
    hash_password,
    rate_limit_key,
    verify_password,
)
from app.verification import consume_code, discard_codes, is_pending_expired, issue_code


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
    return UserPublic(
        id=user.id,
        name=user.public_name,
        email=user.email,
        email_verified=user.email_verified_at is not None,
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _secret(request: Request) -> str:
    return request.app.state.settings.jwt_secret.get_secret_value()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _limit_ip(
    request: Request,
    session: Session,
    *,
    scope: str,
    window: timedelta,
    limit: int,
) -> None:
    key = rate_limit_key(_secret(request), scope, _client_ip(request))
    count = consume_attempt(session, scope=scope, key_hash=key, window=window)
    session.commit()
    if count > limit:
        raise ApiError(
            429,
            "too_many_requests",
            "Muitas solicitações deste endereço. Tente novamente mais tarde.",
        )


def _require_email_delivery(request: Request) -> None:
    if not request.app.state.settings.email_verification_enabled:
        raise ApiError(
            503,
            "email_unavailable",
            "O envio de e-mails está temporariamente indisponível.",
        )


def _invalid_code_error() -> ApiError:
    return ApiError(400, "invalid_verification_code", "Código inválido ou expirado.")


def _user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email).with_for_update())


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    user: UserPublic
    email: EmailMessage | None


def create_user(payload: UserCreate, request: Request, session: Session) -> RegistrationResult:
    _limit_ip(request, session, scope="register", window=REGISTER_WINDOW, limit=REGISTER_LIMIT)
    settings = request.app.state.settings
    email = str(payload.email)
    now = _utcnow()

    existing = _user_by_email(session, email)
    if existing is not None:
        if not is_pending_expired(existing, now):
            raise ApiError(409, "email_already_registered", "Este e-mail já está cadastrado.")
        # Cadastro pendente abandonado: não pode ter produtos nem avaliações.
        session.delete(existing)
        session.flush()

    user = User(
        public_name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        created_at=now,
        email_verified_at=None if settings.email_verification_enabled else now,
    )
    session.add(user)
    try:
        session.flush()
        message = None
        if settings.email_verification_enabled:
            code = issue_code(
                session, user=user, purpose="email_verification", secret=_secret(request), now=now
            )
            message = verification_email(user.email, user.public_name, code) if code else None
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ApiError(409, "email_already_registered", "Este e-mail já está cadastrado.") from exc
    session.refresh(user)
    return RegistrationResult(_public_user(user), message)


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
    if user.email_verified_at is None:
        # Só é revelado a quem já provou conhecer a senha.
        raise ApiError(
            403,
            "email_not_verified",
            "Confirme seu e-mail com o código enviado antes de entrar.",
        )
    return TokenResponse(
        access_token=create_access_token(user.id, secret, session_version=user.session_version)
    )


def verify_email(
    payload: EmailVerificationInput, request: Request, session: Session
) -> TokenResponse:
    _limit_ip(request, session, scope="code", window=CODE_WINDOW, limit=CODE_LIMIT)
    user = _user_by_email(session, str(payload.email))
    if user is None or user.email_verified_at is not None:
        raise _invalid_code_error()
    confirmed = consume_code(
        session,
        user=user,
        purpose="email_verification",
        code=payload.code,
        secret=_secret(request),
    )
    if not confirmed:
        # Persiste a tentativa errada antes de responder.
        session.commit()
        raise _invalid_code_error()
    user.email_verified_at = _utcnow()
    session.commit()
    return TokenResponse(
        access_token=create_access_token(
            user.id, _secret(request), session_version=user.session_version
        )
    )


def resend_verification(
    payload: EmailInput, request: Request, session: Session
) -> EmailMessage | None:
    """Sempre responde igual para não revelar quais e-mails existem."""

    _require_email_delivery(request)
    _limit_ip(request, session, scope="email", window=EMAIL_WINDOW, limit=EMAIL_LIMIT)
    user = _user_by_email(session, str(payload.email))
    message = None
    if user is not None and user.email_verified_at is None:
        code = issue_code(
            session, user=user, purpose="email_verification", secret=_secret(request)
        )
        if code:
            message = verification_email(user.email, user.public_name, code)
    session.commit()
    return message


def request_password_reset(
    payload: EmailInput, request: Request, session: Session
) -> EmailMessage | None:
    """Sempre responde igual para não revelar quais e-mails existem."""

    _require_email_delivery(request)
    _limit_ip(request, session, scope="email", window=EMAIL_WINDOW, limit=EMAIL_LIMIT)
    user = _user_by_email(session, str(payload.email))
    message = None
    if user is not None and not is_pending_expired(user):
        code = issue_code(session, user=user, purpose="password_reset", secret=_secret(request))
        if code:
            message = password_reset_email(user.email, user.public_name, code)
    session.commit()
    return message


def confirm_password_reset(
    payload: PasswordResetConfirm, request: Request, session: Session
) -> None:
    _require_email_delivery(request)
    _limit_ip(request, session, scope="code", window=CODE_WINDOW, limit=CODE_LIMIT)
    user = _user_by_email(session, str(payload.email))
    if user is None:
        raise _invalid_code_error()
    confirmed = consume_code(
        session,
        user=user,
        purpose="password_reset",
        code=payload.code,
        secret=_secret(request),
    )
    if not confirmed:
        session.commit()
        raise _invalid_code_error()

    now = _utcnow()
    user.password_hash = hash_password(payload.new_password)
    # Receber o código prova a posse do e-mail, inclusive de conta pendente.
    if user.email_verified_at is None:
        user.email_verified_at = now
    user.session_version += 1
    discard_codes(session, user=user)
    reset_attempts(
        session,
        scope="account",
        key_hash=rate_limit_key(_secret(request), "account", user.email),
    )
    session.commit()


def _resolve_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials,
    session: Session,
) -> User:
    if credentials.scheme.casefold() != "bearer":
        raise _authentication_error()
    try:
        claims = decode_access_token_claims(
            credentials.credentials,
            request.app.state.settings.jwt_secret.get_secret_value(),
        )
    except ValueError:
        raise _authentication_error() from None
    user = session.get(User, claims.user_id)
    if user is None or user.email_verified_at is None:
        raise _authentication_error()
    if claims.session_version != user.session_version:
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


def current_user_response(
    request: Request, user: User = Depends(get_current_user)
) -> UserPublic:
    public = _public_user(user)
    public.is_admin = user.email in request.app.state.settings.admin_email_set
    return public
