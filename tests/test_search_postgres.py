"""Busca no banco contra PostgreSQL real, com pg_trgm.

Roda apenas no PostgreSQL efêmero do GitHub Actions, em schema exclusivo.
"""

from __future__ import annotations

from decimal import Decimal
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.catalog import search_products
from app.models import Base, Product, User


def _ci_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL não foi definido")
    parsed = make_url(database_url)
    if os.getenv("GITHUB_ACTIONS") != "true" or parsed.host not in {"127.0.0.1", "localhost"}:
        pytest.skip("teste destrutivo permitido apenas no PostgreSQL efêmero do GitHub Actions")
    return database_url


@pytest.fixture
def session():
    database_url = _ci_database_url()
    admin_engine = create_engine(database_url)
    schema = f"search_{uuid4().hex}"
    with admin_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    try:
        with sessionmaker(bind=engine, expire_on_commit=False)() as database_session:
            owner = User(public_name="Ana", email="ana@example.com", password_hash="x")
            database_session.add(owner)
            database_session.flush()
            for index, (name, brand, category) in enumerate(
                (
                    ("Arroz integral", "Tio João", "food"),
                    ("Arroz parboilizado", "Camil", "food"),
                    ("Café tradicional", "Pilão", "food"),
                    ("Sabão líquido", "Omo", "cleaning"),
                    ("Leite 50% menos gordura", "Italac", "food"),
                    ("Detergente neutro", "Ypê", "cleaning"),
                )
            ):
                database_session.add(
                    Product(
                        responsible_id=owner.id, name=name, brand=brand, quantity=Decimal("1"),
                        unit="un", category=category, identity_key=f"produto-{index}",
                    )
                )
            database_session.commit()
            yield database_session
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def search(session, **filters):
    values = {"current_user": None, "name": None, "brand": None, "category": None, "barcode": None, "page": 1, "page_size": 20}
    values.update(filters)
    return search_products(session, **values)


def names(page):
    return [item.name for item in page.items]


def test_exact_search_filters_orders_and_paginates_in_the_database(session):
    first = search(session, name="ARROZ", page_size=1)
    second = search(session, name="arroz", page=2, page_size=1)
    assert (first.total, names(first), names(second)) == (2, ["Arroz integral"], ["Arroz parboilizado"])
    assert first.approximate is False
    assert names(search(session, name="cafe", brand="pilao")) == ["Café tradicional"]
    assert names(search(session, category="cleaning")) == ["Detergente neutro", "Sabão líquido"]


def test_wildcards_in_the_term_are_literal(session):
    assert names(search(session, name="50%")) == ["Leite 50% menos gordura"]
    assert search(session, name="a_r").total == 0


def test_typos_fall_back_to_similar_products(session):
    result = search(session, name="arros")
    assert result.approximate is True
    assert names(result) == ["Arroz integral", "Arroz parboilizado"]

    brand = search(session, brand="pilaõ", name="cafe tradicinal")
    assert (brand.approximate, names(brand)) == (True, ["Café tradicional"])


def test_approximate_search_keeps_the_category_and_rejects_distant_terms(session):
    assert search(session, name="arros", category="cleaning").total == 0
    unrelated = search(session, name="ypioca")
    assert (unrelated.total, unrelated.approximate, unrelated.items) == (0, False, [])
