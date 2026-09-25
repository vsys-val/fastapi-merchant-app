"""Painel administrativo: visão consolidada de uso, catálogo e operação."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from time import perf_counter
from typing import Any

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.errors import ApiError
from app.models import User
from app.observability import LATENCY_BUCKETS_MS, percentile_from_buckets


TIMEZONE = "America/Sao_Paulo"


def is_admin(request: Request, user: User) -> bool:
    return user.email in request.app.state.settings.admin_email_set


def require_admin(request: Request, user: User = Depends(get_current_user)) -> User:
    if not is_admin(request, user):
        raise ApiError(403, "admin_required", "Acesso restrito à administração.")
    return user


def _pct(part: float, whole: float) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def _scalar(session: Session, sql: str, **params: Any) -> Any:
    return session.execute(text(sql), params).scalar()


def _rows(session: Session, sql: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in session.execute(text(sql), params).mappings()]


def _system(request: Request, session: Session, now: datetime) -> dict[str, Any]:
    settings = request.app.state.settings
    metrics = getattr(request.app.state, "request_metrics", None)
    try:
        started = perf_counter()
        session.execute(text("SELECT 1")).scalar_one()
        database = {"status": "available", "latency_ms": round((perf_counter() - started) * 1000, 1)}
    except SQLAlchemyError:
        session.rollback()
        database = {"status": "unavailable", "latency_ms": None}
    return {
        "environment": settings.environment,
        "api_commit": settings.render_git_commit,
        "email_delivery": settings.email_delivery,
        "uptime_seconds": int((now - metrics.started_at).total_seconds()) if metrics else None,
        "database": database,
    }


def _totals(session: Session) -> dict[str, int]:
    row = session.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM usuarios) AS users,
              (SELECT count(*) FROM usuarios WHERE email_verificado_em IS NOT NULL) AS users_verified,
              (SELECT count(*) FROM produtos WHERE excluido_em IS NULL) AS products_active,
              (SELECT count(*) FROM produtos WHERE excluido_em IS NOT NULL) AS products_deleted,
              (SELECT count(*) FROM avaliacoes) AS reviews,
              (SELECT count(*) FROM avaliacoes WHERE comentario IS NOT NULL) AS reviews_with_comment
            """
        )
    ).mappings().one()
    totals = dict(row)
    totals["users_pending"] = totals["users"] - totals["users_verified"]
    return totals


def _daily(session: Session, since: datetime, days: int, today: date) -> list[dict[str, Any]]:
    """Séries por dia no fuso de São Paulo, com zero nos dias sem registro."""

    def by_day(sql: str) -> dict[date, int]:
        return {row["day"]: row["total"] for row in _rows(session, sql, since=since, tz=TIMEZONE)}

    users = by_day("SELECT (criado_em AT TIME ZONE :tz)::date AS day, count(*) AS total FROM usuarios WHERE criado_em >= :since GROUP BY 1")
    products = by_day("SELECT (criado_em AT TIME ZONE :tz)::date AS day, count(*) AS total FROM produtos WHERE criado_em >= :since GROUP BY 1")
    reviews = by_day("SELECT (criado_em AT TIME ZONE :tz)::date AS day, count(*) AS total FROM avaliacoes WHERE criado_em >= :since GROUP BY 1")
    active = by_day("SELECT (criado_em AT TIME ZONE :tz)::date AS day, count(DISTINCT usuario_id) AS total FROM eventos_produto WHERE criado_em >= :since AND usuario_id IS NOT NULL GROUP BY 1")
    sessions = by_day("SELECT (criado_em AT TIME ZONE :tz)::date AS day, count(DISTINCT sessao) AS total FROM eventos_produto WHERE criado_em >= :since GROUP BY 1")
    searches = by_day("SELECT (criado_em AT TIME ZONE :tz)::date AS day, count(*) AS total FROM eventos_produto WHERE criado_em >= :since AND nome = 'search_performed' GROUP BY 1")

    series = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        series.append(
            {
                "date": day.isoformat(),
                "new_users": users.get(day, 0),
                "new_products": products.get(day, 0),
                "new_reviews": reviews.get(day, 0),
                "active_users": active.get(day, 0),
                "sessions": sessions.get(day, 0),
                "searches": searches.get(day, 0),
            }
        )
    return series


def _event_count(session: Session, name: str, since: datetime, condition: str = "true") -> int:
    return _scalar(
        session,
        f"SELECT count(*) FROM eventos_produto WHERE nome = :name AND criado_em >= :since AND {condition}",
        name=name,
        since=since,
    ) or 0


def _product_metrics(session: Session, since: datetime, now: datetime) -> dict[str, Any]:
    week_ago = now - timedelta(days=7)
    own_views = _event_count(session, "product_viewed", week_ago, "(propriedades->>'own_review')::boolean")
    weekly_active = _scalar(
        session,
        "SELECT count(DISTINCT usuario_id) FROM eventos_produto WHERE criado_em >= :since AND usuario_id IS NOT NULL",
        since=week_ago,
    ) or 0

    searches = _event_count(session, "search_performed", since)
    # Sugestões aproximadas não contam como cobertura do catálogo: o produto
    # buscado pode não existir. Elas têm indicador próprio.
    approximate = _event_count(session, "search_performed", since, "(propriedades->>'approximate')::boolean IS TRUE")
    with_results = _event_count(
        session,
        "search_performed",
        since,
        "(propriedades->>'results')::int > 0 AND (propriedades->>'approximate')::boolean IS NOT TRUE",
    )
    barcode = _event_count(session, "search_performed", since, "propriedades->>'mode' = 'barcode'")

    # Coorte: contas criadas na janela com pelo menos 7 dias de vida.
    cohort = session.execute(
        text(
            """
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM avaliacoes a
                       WHERE a.usuario_id = u.id AND a.criado_em < u.criado_em + interval '7 days'
                   )) AS activated
            FROM usuarios u
            WHERE u.criado_em >= :since AND u.criado_em <= :cutoff
            """
        ),
        {"since": since, "cutoff": now - timedelta(days=7)},
    ).mappings().one()

    active_users = _scalar(
        session,
        "SELECT count(DISTINCT usuario_id) FROM eventos_produto WHERE criado_em >= :since AND usuario_id IS NOT NULL",
        since=since,
    ) or 0
    reviews_in_window = _scalar(session, "SELECT count(*) FROM avaliacoes WHERE criado_em >= :since", since=since) or 0

    funnel_steps = []
    for label, condition in (
        ("Etapa 1 · experiência", "nome = 'review_step_viewed' AND propriedades->>'step' = '1'"),
        ("Etapa 2 · motivos", "nome = 'review_step_viewed' AND propriedades->>'step' = '2'"),
        ("Etapa 3 · conferência", "nome = 'review_step_viewed' AND propriedades->>'step' = '3'"),
        ("Publicada", "nome = 'review_saved'"),
    ):
        sessions = _scalar(
            session,
            f"SELECT count(DISTINCT sessao) FROM eventos_produto WHERE criado_em >= :since AND {condition}",
            since=since,
        ) or 0
        funnel_steps.append({"step": label, "sessions": sessions})
    first_step = funnel_steps[0]["sessions"]
    published = funnel_steps[-1]["sessions"]

    submitted = _event_count(session, "product_create_submitted", since)
    created = _event_count(session, "product_created", since)
    conflicts = _event_count(session, "product_create_conflict", since)

    return {
        "north_star": {
            "label": "Consultas a produtos já avaliados, por usuário ativo, nos últimos 7 dias",
            "value": round(own_views / weekly_active, 2) if weekly_active else None,
            "own_review_views": own_views,
            "weekly_active_users": weekly_active,
            "target": 2,
        },
        "searches": {
            "total": searches,
            "with_results_pct": _pct(with_results, searches),
            "barcode_pct": _pct(barcode, searches),
            "approximate_pct": _pct(approximate, searches),
            "target_with_results_pct": 70,
        },
        "activation": {
            "cohort": cohort["total"],
            "activated": cohort["activated"],
            "pct": _pct(cohort["activated"], cohort["total"]),
            "target_pct": 40,
        },
        "reviews_per_active_user": round(reviews_in_window / active_users, 2) if active_users else None,
        "review_funnel": {
            "steps": funnel_steps,
            "abandonment_pct": _pct(first_step - published, first_step) if first_step else None,
            "target_abandonment_pct": 30,
        },
        "product_creation": {
            "submitted": submitted,
            "created": created,
            "conflicts": conflicts,
            "conflict_pct": _pct(conflicts, submitted),
            "target_conflict_pct": 10,
        },
        "signups_completed": _event_count(session, "signup_completed", since),
    }


def _catalog(session: Session) -> dict[str, Any]:
    active_products = _scalar(session, "SELECT count(*) FROM produtos WHERE excluido_em IS NULL") or 0
    without_reviews = _scalar(
        session,
        "SELECT count(*) FROM produtos p WHERE p.excluido_em IS NULL AND NOT EXISTS (SELECT 1 FROM avaliacoes a WHERE a.produto_id = p.id)",
    ) or 0
    repurchase = {row["value"]: row["total"] for row in _rows(session, "SELECT intencao_recompra AS value, count(*) AS total FROM avaliacoes GROUP BY 1")}
    return {
        "by_category": _rows(
            session,
            "SELECT categoria AS category, count(*) AS products FROM produtos WHERE excluido_em IS NULL GROUP BY 1 ORDER BY 2 DESC, 1",
        ),
        "products_without_reviews_pct": _pct(without_reviews, active_products),
        "top_products": _rows(
            session,
            """
            SELECT p.id, p.nome AS name, p.marca AS brand, count(a.id) AS reviews
            FROM produtos p JOIN avaliacoes a ON a.produto_id = p.id
            WHERE p.excluido_em IS NULL
            GROUP BY p.id ORDER BY reviews DESC, p.nome LIMIT 5
            """,
        ),
        "aspects": _rows(
            session,
            """
            SELECT aspecto AS aspect,
                   count(*) FILTER (WHERE percepcao = 'positive') AS positive,
                   count(*) FILTER (WHERE percepcao = 'negative') AS negative
            FROM motivos_avaliacao GROUP BY 1 ORDER BY count(*) DESC, 1
            """,
        ),
        "repurchase": {key: repurchase.get(key, 0) for key in ("yes", "maybe", "no")},
    }


def _bucket_sums(session: Session, where: str, group: str, **params: Any) -> dict[Any, list[int]]:
    """Soma as faixas de duração por grupo, no próprio banco."""

    result: dict[Any, list[int]] = {}
    for row in _rows(
        session,
        f"""
        SELECT {group} AS grp, u.ord AS ord, sum(u.value) AS total
        FROM metricas_requisicoes m, unnest(m.faixas) WITH ORDINALITY AS u(value, ord)
        WHERE {where}
        GROUP BY 1, 2
        """,
        **params,
    ):
        buckets = result.setdefault(row["grp"], [0] * (len(LATENCY_BUCKETS_MS) + 1))
        buckets[row["ord"] - 1] = int(row["total"])
    return result


def _technical(session: Session, since: datetime, now: datetime, days: int, today: date) -> dict[str, Any]:
    totals = session.execute(
        text(
            """
            SELECT coalesce(sum(contagem), 0) AS requests,
                   coalesce(sum(contagem) FILTER (WHERE classe = 4), 0) AS errors_4xx,
                   coalesce(sum(contagem) FILTER (WHERE classe = 5), 0) AS errors_5xx
            FROM metricas_requisicoes WHERE minuto >= :since
            """
        ),
        {"since": since},
    ).mappings().one()
    overall = _bucket_sums(session, "m.minuto >= :since", "1", since=since).get(1, [])

    per_day = {
        row["day"]: row
        for row in _rows(
            session,
            """
            SELECT (minuto AT TIME ZONE :tz)::date AS day,
                   sum(contagem) AS requests,
                   coalesce(sum(contagem) FILTER (WHERE classe = 5), 0) AS errors_5xx
            FROM metricas_requisicoes WHERE minuto >= :since GROUP BY 1
            """,
            since=since,
            tz=TIMEZONE,
        )
    }
    day_buckets = _bucket_sums(session, "m.minuto >= :since", "(m.minuto AT TIME ZONE :tz)::date", since=since, tz=TIMEZONE)
    daily = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        row = per_day.get(day)
        daily.append(
            {
                "date": day.isoformat(),
                "requests": int(row["requests"]) if row else 0,
                "errors_5xx": int(row["errors_5xx"]) if row else 0,
                "p95_ms": percentile_from_buckets(day_buckets.get(day, []), 0.95),
            }
        )

    last_day = now - timedelta(hours=24)
    route_buckets = _bucket_sums(session, "m.minuto >= :since", "m.metodo || ' ' || m.rota", since=last_day)
    routes = []
    for row in _rows(
        session,
        """
        SELECT metodo AS method, rota AS route, sum(contagem) AS requests,
               coalesce(sum(contagem) FILTER (WHERE classe = 5), 0) AS errors_5xx,
               coalesce(sum(contagem) FILTER (WHERE classe = 4), 0) AS errors_4xx,
               sum(duracao_total_ms) / NULLIF(sum(contagem), 0) AS avg_ms,
               max(duracao_max_ms) AS max_ms
        FROM metricas_requisicoes WHERE minuto >= :since
        GROUP BY 1, 2 ORDER BY requests DESC LIMIT 15
        """,
        since=last_day,
    ):
        requests = int(row["requests"])
        routes.append(
            {
                "method": row["method"],
                "route": row["route"],
                "requests": requests,
                "error_4xx_pct": _pct(int(row["errors_4xx"]), requests),
                "error_5xx_pct": _pct(int(row["errors_5xx"]), requests),
                "avg_ms": round(float(row["avg_ms"]), 1) if row["avg_ms"] is not None else None,
                "p95_ms": percentile_from_buckets(route_buckets.get(f"{row['method']} {row['route']}", []), 0.95),
                "max_ms": round(float(row["max_ms"]), 1),
            }
        )

    requests = int(totals["requests"])
    return {
        "requests": requests,
        "error_4xx_pct": _pct(int(totals["errors_4xx"]), requests),
        "error_5xx_pct": _pct(int(totals["errors_5xx"]), requests),
        "p95_ms": percentile_from_buckets(overall, 0.95),
        "target_p95_ms": 800,
        "latency_buckets_ms": list(LATENCY_BUCKETS_MS),
        "daily": daily,
        "routes_24h": routes,
    }


def _frontend(session: Session, since: datetime) -> dict[str, Any]:
    return {
        "loads": _event_count(session, "app_loaded", since),
        "versions": _rows(
            session,
            """
            SELECT coalesce(propriedades->>'commit', 'desconhecido') AS commit,
                   count(DISTINCT sessao) AS sessions, max(criado_em) AS last_seen
            FROM eventos_produto WHERE nome = 'app_loaded' AND criado_em >= :since
            GROUP BY 1 ORDER BY last_seen DESC LIMIT 5
            """,
            since=since,
        ),
        "errors_total": _event_count(session, "client_error", since),
        "top_errors": _rows(
            session,
            """
            SELECT coalesce(propriedades->>'message', 'sem mensagem') AS message,
                   count(*) AS count, max(criado_em) AS last_seen
            FROM eventos_produto WHERE nome = 'client_error' AND criado_em >= :since
            GROUP BY 1 ORDER BY count DESC, last_seen DESC LIMIT 5
            """,
            since=since,
        ),
    }


def build_overview(request: Request, session: Session, days: int, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    since = current - timedelta(days=days)
    today = _scalar(session, "SELECT (:now AT TIME ZONE :tz)::date", now=current, tz=TIMEZONE)
    return {
        "generated_at": current,
        "window_days": days,
        "timezone": TIMEZONE,
        "system": _system(request, session, current),
        "totals": _totals(session),
        "daily": _daily(session, since, days, today),
        "product": _product_metrics(session, since, current),
        "catalog": _catalog(session),
        "technical": _technical(session, since, current, days, today),
        "frontend": _frontend(session, since),
    }
