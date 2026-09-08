"""Limitação de login persistida e atômica no PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import LoginAttempt


ACCOUNT_WINDOW = timedelta(minutes=15)
ACCOUNT_LIMIT = 5
IP_WINDOW = timedelta(minutes=1)
IP_LIMIT = 20


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def active_attempt_count(
    session: Session,
    *,
    scope: str,
    key_hash: str,
    window: timedelta,
    now: datetime | None = None,
) -> int:
    current_time = now or _utcnow()
    row = session.scalar(
        select(LoginAttempt).where(
            LoginAttempt.scope == scope,
            LoginAttempt.key_hash == key_hash,
        )
    )
    if row is None or row.window_started_at <= current_time - window:
        return 0
    return row.attempts


def consume_attempt(
    session: Session,
    *,
    scope: str,
    key_hash: str,
    window: timedelta,
    now: datetime | None = None,
) -> int:
    """Incrementa ou reinicia o contador em uma única instrução atômica."""

    current_time = now or _utcnow()
    cutoff = current_time - window
    statement = insert(LoginAttempt).values(
        scope=scope,
        key_hash=key_hash,
        attempts=1,
        window_started_at=current_time,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[LoginAttempt.scope, LoginAttempt.key_hash],
        set_={
            LoginAttempt.attempts: case(
                (LoginAttempt.window_started_at <= cutoff, 1),
                else_=LoginAttempt.attempts + 1,
            ),
            LoginAttempt.window_started_at: case(
                (LoginAttempt.window_started_at <= cutoff, current_time),
                else_=LoginAttempt.window_started_at,
            ),
        },
    ).returning(LoginAttempt.attempts)
    return session.execute(statement).scalar_one()


def reset_attempts(session: Session, *, scope: str, key_hash: str) -> None:
    session.execute(
        delete(LoginAttempt).where(
            LoginAttempt.scope == scope,
            LoginAttempt.key_hash == key_hash,
        )
    )
