"""Alertas de operação: guarda-corpos avaliados sobre a última hora.

A mesma avaliação alimenta o painel e o endpoint consultado pelo workflow
agendado do GitHub Actions, que abre ou fecha uma issue de alerta
(ADR-0015). Cada verificação exige volume mínimo para não alarmar com
duas ou três requisições.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
from typing import Any

from fastapi import Header, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.observability import ABOVE_LAST_BUCKET_MS, LATENCY_BUCKETS_MS, percentile_from_buckets


WINDOW = timedelta(hours=1)
# Menos que isso na janela não sustenta uma porcentagem nem um p95.
MIN_REQUESTS = 20
MAX_5XX_PCT = 5.0
# Guarda-corpo da visão de produto: p95 da busca < 800 ms.
SEARCH_ROUTE = ("GET", "/api/v1/products")
MAX_SEARCH_P95_MS = 800
# Erros do navegador contam por sessão, para um único aparelho quebrado não alarmar.
MAX_CLIENT_ERROR_SESSIONS = 5


def _check(key: str, label: str, ok: bool, value: Any, threshold: str, detail: str) -> dict[str, Any]:
    return {"key": key, "label": label, "ok": ok, "value": value, "threshold": threshold, "detail": detail}


def _buckets(session: Session, where: str, **params: Any) -> list[int]:
    buckets = [0] * (len(LATENCY_BUCKETS_MS) + 1)
    for ord_, total in session.execute(
        text(
            f"""
            SELECT u.ord, sum(u.value)
            FROM metricas_requisicoes m, unnest(m.faixas) WITH ORDINALITY AS u(value, ord)
            WHERE {where}
            GROUP BY 1
            """
        ),
        params,
    ):
        buckets[ord_ - 1] = int(total)
    return buckets


def evaluate_alerts(session: Session, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    since = current - WINDOW
    checks: list[dict[str, Any]] = []

    try:
        session.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        session.rollback()
        checks.append(_check("database", "Banco de dados", False, None, "disponível", "O banco não respondeu."))
        return {"status": "alert", "evaluated_at": current.isoformat(), "window_minutes": 60, "checks": checks}
    checks.append(_check("database", "Banco de dados", True, None, "disponível", "Respondendo."))

    requests, errors_5xx = session.execute(
        text(
            "SELECT coalesce(sum(contagem), 0), coalesce(sum(contagem) FILTER (WHERE classe = 5), 0) "
            "FROM metricas_requisicoes WHERE minuto >= :since"
        ),
        {"since": since},
    ).one()
    requests, errors_5xx = int(requests), int(errors_5xx)
    if requests < MIN_REQUESTS:
        checks.append(_check("errors_5xx", "Erros 5xx", True, None, f"< {MAX_5XX_PCT:g}%", f"Volume insuficiente ({requests} requisições)."))
    else:
        pct = round(errors_5xx * 100 / requests, 1)
        checks.append(
            _check("errors_5xx", "Erros 5xx", pct < MAX_5XX_PCT, pct, f"< {MAX_5XX_PCT:g}%", f"{errors_5xx} de {requests} requisições.")
        )

    method, route = SEARCH_ROUTE
    search = _buckets(session, "m.minuto >= :since AND m.metodo = :method AND m.rota = :route", since=since, method=method, route=route)
    searches = sum(search)
    if searches < MIN_REQUESTS:
        checks.append(
            _check("search_p95", "Latência p95 da busca", True, None, f"≤ {MAX_SEARCH_P95_MS} ms", f"Volume insuficiente ({searches} buscas).")
        )
    else:
        p95 = percentile_from_buckets(search, 0.95)
        shown = "> 3.200 ms" if p95 == ABOVE_LAST_BUCKET_MS else f"≤ {p95} ms"
        checks.append(
            _check("search_p95", "Latência p95 da busca", p95 is not None and p95 <= MAX_SEARCH_P95_MS, p95, f"≤ {MAX_SEARCH_P95_MS} ms", f"{shown} em {searches} buscas.")
        )

    sessions = int(
        session.execute(
            text("SELECT count(DISTINCT sessao) FROM eventos_produto WHERE nome = 'client_error' AND criado_em >= :since"),
            {"since": since},
        ).scalar_one()
    )
    checks.append(
        _check(
            "client_errors", "Erros no navegador", sessions < MAX_CLIENT_ERROR_SESSIONS, sessions,
            f"< {MAX_CLIENT_ERROR_SESSIONS} sessões", f"{sessions} sessões com erro na última hora.",
        )
    )

    status = "ok" if all(check["ok"] for check in checks) else "alert"
    return {"status": status, "evaluated_at": current.isoformat(), "window_minutes": 60, "checks": checks}


def require_alerts_token(request: Request, x_alerts_token: str | None = Header(default=None)) -> None:
    """Autentica o workflow de alertas por um segredo compartilhado.

    Sem ``ALERTS_TOKEN`` configurado, o endpoint não existe (404).
    """

    configured = request.app.state.settings.alerts_token
    if configured is None:
        raise ApiError(404, "not_found", "Recurso não encontrado.")
    expected = configured.get_secret_value().encode()
    if x_alerts_token is None or not hmac.compare_digest(x_alerts_token.encode(), expected):
        raise ApiError(401, "invalid_alerts_token", "Token de alertas inválido.")
