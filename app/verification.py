"""Códigos de uso único para confirmar e-mail e redefinir senha."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import User, VerificationCode
from app.security import generate_verification_code, verification_code_hash


Purpose = Literal["email_verification", "password_reset"]

CODE_TTL = timedelta(minutes=15)
CODE_MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)
# Conta não confirmada nesse prazo libera o e-mail para um novo cadastro.
PENDING_ACCOUNT_TTL = timedelta(hours=24)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_pending_expired(user: User, now: datetime | None = None) -> bool:
    current_time = now or _utcnow()
    return user.email_verified_at is None and user.created_at <= current_time - PENDING_ACCOUNT_TTL


def issue_code(
    session: Session,
    *,
    user: User,
    purpose: Purpose,
    secret: str,
    now: datetime | None = None,
) -> str | None:
    """Gera um código novo e invalida o anterior.

    Retorna ``None`` quando o último envio ainda está no intervalo mínimo,
    para que reenvios repetidos não virem uma forma de spam.
    """

    current_time = now or _utcnow()
    existing = session.scalar(
        select(VerificationCode)
        .where(VerificationCode.user_id == user.id, VerificationCode.purpose == purpose)
        .with_for_update()
    )
    if existing is not None and existing.sent_at > current_time - RESEND_COOLDOWN:
        return None

    code = generate_verification_code()
    values = {
        VerificationCode.code_hash: verification_code_hash(secret, user.id, purpose, code),
        VerificationCode.expires_at: current_time + CODE_TTL,
        VerificationCode.attempts: 0,
        VerificationCode.sent_at: current_time,
    }
    statement = insert(VerificationCode).values(
        {VerificationCode.user_id: user.id, VerificationCode.purpose: purpose, **values}
    )
    statement = statement.on_conflict_do_update(
        index_elements=[VerificationCode.user_id, VerificationCode.purpose],
        set_=values,
    )
    session.execute(statement)
    return code


def consume_code(
    session: Session,
    *,
    user: User,
    purpose: Purpose,
    code: str,
    secret: str,
    now: datetime | None = None,
) -> bool:
    """Valida e remove o código. Erros contam tentativas até invalidá-lo."""

    current_time = now or _utcnow()
    row = session.scalar(
        select(VerificationCode)
        .where(VerificationCode.user_id == user.id, VerificationCode.purpose == purpose)
        .with_for_update()
    )
    if row is None:
        return False
    if row.expires_at <= current_time:
        session.delete(row)
        return False

    expected = verification_code_hash(secret, user.id, purpose, code)
    if hmac.compare_digest(row.code_hash, expected):
        session.delete(row)
        return True

    row.attempts += 1
    if row.attempts >= CODE_MAX_ATTEMPTS:
        session.delete(row)
    return False


def discard_codes(session: Session, *, user: User) -> None:
    session.execute(delete(VerificationCode).where(VerificationCode.user_id == user.id))
