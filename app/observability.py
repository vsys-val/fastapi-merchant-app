"""Métricas técnicas da API: requisições agregadas por minuto.

Cada requisição só incrementa contadores em memória. A cada
``FLUSH_INTERVAL_SECONDS`` os minutos acumulados são gravados no PostgreSQL
em um único UPSERT, sem uma escrita por requisição. Uma queda do processo
perde no máximo o intervalo ainda não gravado.
"""

from __future__ import annotations

import asyncio
from bisect import bisect_left
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from threading import Lock
from time import perf_counter
from typing import AsyncIterator, Callable

from fastapi import FastAPI, Request, Response
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.models import ProductEvent, RequestMetric


logger = logging.getLogger(__name__)

FLUSH_INTERVAL_SECONDS = 30
# Limites superiores (ms) das faixas de duração; a última faixa é "acima de 3200".
LATENCY_BUCKETS_MS = (25, 50, 100, 200, 400, 800, 1600, 3200)
METRICS_RETENTION = timedelta(days=90)
EVENTS_RETENTION = timedelta(days=180)
# O health check do Render e os preflights de CORS distorceriam os números.
IGNORED_PATHS = frozenset({"/health"})
UNMATCHED_ROUTE = "<não encontrada>"


def bucket_index(duration_ms: float) -> int:
    return bisect_left(LATENCY_BUCKETS_MS, duration_ms)


# Valor devolvido quando o percentil cai na faixa aberta, acima do último limite.
ABOVE_LAST_BUCKET_MS = LATENCY_BUCKETS_MS[-1] + 1


def percentile_from_buckets(buckets: list[int], percentile: float) -> int | None:
    """Limite superior da faixa que contém o percentil; ``None`` sem dados.

    O resultado é aproximado para cima pela granularidade das faixas.
    ``ABOVE_LAST_BUCKET_MS`` significa "acima de 3200 ms".
    """

    total = sum(buckets)
    if total == 0:
        return None
    threshold = total * percentile
    cumulative = 0
    for index, count in enumerate(buckets):
        cumulative += count
        if cumulative >= threshold:
            return LATENCY_BUCKETS_MS[index] if index < len(LATENCY_BUCKETS_MS) else ABOVE_LAST_BUCKET_MS
    return None


@dataclass
class _Aggregate:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    buckets: list[int] = field(default_factory=lambda: [0] * (len(LATENCY_BUCKETS_MS) + 1))

    def add(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += duration_ms
        self.max_ms = max(self.max_ms, duration_ms)
        self.buckets[bucket_index(duration_ms)] += 1


Key = tuple[datetime, str, str, int]


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._pending: dict[Key, _Aggregate] = {}
        self.started_at = datetime.now(timezone.utc)
        self._last_cleanup: datetime | None = None

    def record(
        self, *, method: str, route: str, status_code: int, duration_ms: float, at: datetime
    ) -> None:
        minute = at.replace(second=0, microsecond=0)
        key = (minute, method, route[:120], min(max(status_code // 100, 1), 5))
        with self._lock:
            self._pending.setdefault(key, _Aggregate()).add(duration_ms)

    def drain(self) -> dict[Key, _Aggregate]:
        with self._lock:
            pending, self._pending = self._pending, {}
        return pending

    def restore(self, pending: dict[Key, _Aggregate]) -> None:
        """Devolve ao buffer o que não pôde ser gravado."""

        with self._lock:
            for key, aggregate in pending.items():
                current = self._pending.setdefault(key, _Aggregate())
                current.count += aggregate.count
                current.total_ms += aggregate.total_ms
                current.max_ms = max(current.max_ms, aggregate.max_ms)
                current.buckets = [a + b for a, b in zip(current.buckets, aggregate.buckets)]

    def flush(self, session: Session, now: datetime | None = None) -> int:
        pending = self.drain()
        if not pending:
            return 0
        rows = [
            {
                "minuto": minute,
                "metodo": method,
                "rota": route,
                "classe": status_class,
                "contagem": aggregate.count,
                "total": aggregate.total_ms,
                "maximo": aggregate.max_ms,
                "faixas": aggregate.buckets,
            }
            for (minute, method, route, status_class), aggregate in pending.items()
        ]
        try:
            session.execute(
                text(
                    """
                    INSERT INTO metricas_requisicoes AS m
                        (minuto, metodo, rota, classe, contagem,
                         duracao_total_ms, duracao_max_ms, faixas)
                    VALUES (:minuto, :metodo, :rota, :classe, :contagem,
                            :total, :maximo, :faixas)
                    ON CONFLICT (minuto, metodo, rota, classe) DO UPDATE SET
                        contagem = m.contagem + EXCLUDED.contagem,
                        duracao_total_ms = m.duracao_total_ms + EXCLUDED.duracao_total_ms,
                        duracao_max_ms = GREATEST(m.duracao_max_ms, EXCLUDED.duracao_max_ms),
                        faixas = ARRAY(
                            SELECT a + b FROM unnest(m.faixas, EXCLUDED.faixas) AS t(a, b)
                        )
                    """
                ),
                rows,
            )
            self._cleanup(session, now or datetime.now(timezone.utc))
            session.commit()
        except Exception:
            session.rollback()
            self.restore(pending)
            raise
        return len(rows)

    def _cleanup(self, session: Session, now: datetime) -> None:
        """Retenção limitada, executada no máximo uma vez por hora."""

        if self._last_cleanup and now - self._last_cleanup < timedelta(hours=1):
            return
        session.execute(delete(RequestMetric).where(RequestMetric.minute < now - METRICS_RETENTION))
        session.execute(delete(ProductEvent).where(ProductEvent.created_at < now - EVENTS_RETENTION))
        self._last_cleanup = now


def install_request_metrics(
    application: FastAPI,
    metrics: RequestMetrics,
    session_factory: Callable[[], Session],
) -> None:
    application.state.request_metrics = metrics

    @application.middleware("http")
    async def measure(request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path in IGNORED_PATHS:
            return await call_next(request)
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", None) or UNMATCHED_ROUTE
            metrics.record(
                method=request.method,
                route=route,
                status_code=status_code,
                duration_ms=(perf_counter() - started) * 1000,
                at=datetime.now(timezone.utc),
            )

    def flush_now() -> None:
        try:
            with session_factory() as session:
                metrics.flush(session)
        except Exception as exc:  # noqa: BLE001 - métricas nunca derrubam a API
            logger.warning("Não foi possível gravar métricas de requisição: %s", type(exc).__name__)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        async def periodic_flush() -> None:
            while True:
                await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
                await asyncio.to_thread(flush_now)

        task = asyncio.create_task(periodic_flush())
        try:
            yield
        finally:
            task.cancel()
            await asyncio.to_thread(flush_now)

    application.router.lifespan_context = lifespan
