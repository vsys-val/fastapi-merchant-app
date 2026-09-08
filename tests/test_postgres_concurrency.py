"""Testes de concorrência executados contra o PostgreSQL efêmero do CI.

O módulo é ignorado fora do GitHub Actions. Cada execução cria um schema
exclusivo e só o remove depois dos testes, sem tocar no schema ``public``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from queue import Queue
from threading import Barrier, Event, Thread
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.errors import ApiError
from app.models import Base, Product, Review, User
from app.products import delete_product


@dataclass(frozen=True)
class PostgresHarness:
    engine: Engine
    sessions: sessionmaker[Session]


def _ci_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL não foi definido")

    parsed = make_url(database_url)
    is_local = parsed.host in {"127.0.0.1", "localhost"}
    if os.getenv("GITHUB_ACTIONS") != "true" or not is_local:
        pytest.skip("teste destrutivo permitido apenas no PostgreSQL efêmero do GitHub Actions")
    return database_url


@pytest.fixture(scope="module")
def postgres() -> PostgresHarness:
    database_url = _ci_database_url()
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    schema = f"delivery8_{uuid4().hex}"

    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={schema}"},
    )
    Base.metadata.create_all(engine)

    try:
        yield PostgresHarness(
            engine=engine,
            sessions=sessionmaker(bind=engine, expire_on_commit=False),
        )
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def _seed_product(postgres: PostgresHarness, suffix: str) -> tuple[int, int, int]:
    with postgres.sessions() as session:
        owner = User(
            public_name="Responsável",
            email=f"owner-{suffix}@example.test",
            password_hash="not-used",
        )
        reviewer = User(
            public_name="Avaliador",
            email=f"reviewer-{suffix}@example.test",
            password_hash="not-used",
        )
        session.add_all([owner, reviewer])
        session.flush()
        product = Product(
            responsible_id=owner.id,
            name=f"Produto {suffix}",
            brand="Marca",
            quantity=Decimal("1.000"),
            unit="un",
            category="other",
            identity_key=f"produto|marca||1.000|un|{suffix}",
        )
        session.add(product)
        session.commit()
        return owner.id, reviewer.id, product.id


def _new_review(*, author_id: int, product_id: int) -> Review:
    return Review(
        author_id=author_id,
        product_id=product_id,
        repurchase_intent="yes",
        quality="high",
        expectation="met",
        value_for_money="good",
        comment=None,
    )


def test_unique_review_constraint_survives_concurrent_commits(
    postgres: PostgresHarness,
) -> None:
    _, reviewer_id, product_id = _seed_product(postgres, f"unique-{uuid4().hex}")
    ready = Barrier(2)
    outcomes: Queue[str] = Queue()

    def insert_review() -> None:
        with postgres.sessions() as session:
            session.add(_new_review(author_id=reviewer_id, product_id=product_id))
            ready.wait(timeout=5)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                outcomes.put(f"conflict:{getattr(exc.orig, 'sqlstate', None)}:{constraint_name}")
            else:
                outcomes.put("created")

    workers = [Thread(target=insert_review, daemon=True) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)

    assert all(not worker.is_alive() for worker in workers)
    assert sorted(outcomes.get_nowait() for _ in range(2)) == [
        "conflict:23505:uq_avaliacoes_usuario_produto",
        "created",
    ]
    with postgres.sessions() as session:
        count = session.scalar(
            select(func.count(Review.id)).where(
                Review.author_id == reviewer_id,
                Review.product_id == product_id,
            )
        )
    assert count == 1


def test_review_commit_wins_before_concurrent_product_delete(
    postgres: PostgresHarness,
) -> None:
    owner_id, reviewer_id, product_id = _seed_product(postgres, f"delete-{uuid4().hex}")
    delete_started = Event()
    backend_pid: Queue[int] = Queue()
    outcome: Queue[tuple[int, str]] = Queue()

    reviewer_session = postgres.sessions()
    reviewer_session.scalar(
        select(Product)
        .where(Product.id == product_id)
        .with_for_update(read=True, key_share=True)
    )
    reviewer_session.add(_new_review(author_id=reviewer_id, product_id=product_id))
    reviewer_session.flush()

    def delete_in_parallel() -> None:
        with postgres.sessions() as session:
            owner = session.get(User, owner_id)
            assert owner is not None
            pid = session.scalar(text("SELECT pg_backend_pid()"))
            assert pid is not None
            backend_pid.put(pid)
            delete_started.set()
            try:
                delete_product(product_id, owner, session)
            except ApiError as exc:
                session.rollback()
                outcome.put((exc.status_code, exc.code))
            else:
                outcome.put((204, "deleted"))

    worker = Thread(target=delete_in_parallel, daemon=True)
    worker.start()
    assert delete_started.wait(timeout=5)
    pid = backend_pid.get(timeout=5)

    lock_observed = False
    try:
        deadline = monotonic() + 5
        while monotonic() < deadline:
            with postgres.engine.connect() as connection:
                lock_observed = connection.scalar(
                    text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM pg_catalog.pg_stat_activity "
                        "WHERE pid = :pid AND wait_event_type = 'Lock'"
                        ")"
                    ),
                    {"pid": pid},
                )
            if lock_observed:
                break
            sleep(0.05)

        if lock_observed:
            reviewer_session.commit()
        else:
            reviewer_session.rollback()
    finally:
        reviewer_session.close()
        worker.join(timeout=10)

    assert lock_observed, "a exclusão não aguardou o bloqueio da avaliação"
    assert not worker.is_alive()
    assert outcome.get_nowait() == (409, "product_has_reviews")
    with postgres.sessions() as session:
        product = session.get(Product, product_id)
        assert product is not None
        assert product.deleted_at is None
        assert session.scalar(
            select(func.count(Review.id)).where(Review.product_id == product_id)
        ) == 1
