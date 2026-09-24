"""Eventos de uso enviados pela interface.

Só nomes previstos são aceitos, e as propriedades são escalares curtos: a
interface nunca envia texto digitado, e-mail ou outro dado pessoal. O
usuário é associado apenas quando há um token válido.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import ProductEvent, User
from app.rate_limit import consume_attempt
from app.security import rate_limit_key


EventName = Literal[
    "app_loaded",
    "client_error",
    "search_performed",
    "product_viewed",
    "review_step_viewed",
    "review_saved",
    "product_create_submitted",
    "product_created",
    "product_create_conflict",
    "product_edit_saved",
    "signup_completed",
]

EVENTS_WINDOW = timedelta(hours=1)
EVENTS_LIMIT = 120  # requisições (lotes) por IP por hora
PropertyValue = str | int | float | bool | None


class EventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: EventName
    properties: dict[str, PropertyValue] = Field(default_factory=dict, max_length=8)

    @field_validator("properties")
    @classmethod
    def limit_properties(cls, value: dict[str, PropertyValue]) -> dict[str, PropertyValue]:
        cleaned: dict[str, PropertyValue] = {}
        for key, item in value.items():
            if not key.isidentifier() or len(key) > 30:
                raise ValueError("Nome de propriedade inválido.")
            cleaned[key] = item[:200] if isinstance(item, str) else item
        return cleaned


class EventBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    events: list[EventInput] = Field(min_length=1, max_length=20)


def record_events(
    batch: EventBatch,
    request: Request,
    session: Session,
    user: User | None,
) -> None:
    secret = request.app.state.settings.jwt_secret.get_secret_value()
    client_ip = request.client.host if request.client else "unknown"
    count = consume_attempt(
        session,
        scope="events",
        key_hash=rate_limit_key(secret, "events", client_ip),
        window=EVENTS_WINDOW,
    )
    if count > EVENTS_LIMIT:
        session.commit()
        raise ApiError(429, "too_many_requests", "Muitas solicitações deste endereço. Tente novamente mais tarde.")
    session.execute(
        insert(ProductEvent),
        [
            {
                "name": event.name,
                "session_id": batch.session_id,
                "user_id": user.id if user else None,
                "properties": event.properties,
            }
            for event in batch.events
        ],
    )
    session.commit()


def optional_user_ignoring_errors(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    session: Session,
) -> User | None:
    """Métricas nunca falham por causa de um token vencido: o evento fica anônimo."""

    if credentials is None:
        return None
    from app.auth import _resolve_authenticated_user

    try:
        return _resolve_authenticated_user(request, credentials, session)
    except ApiError:
        return None
