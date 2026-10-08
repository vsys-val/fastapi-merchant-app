"""Local SQLite tests: metadata backfill must never take over user content."""
import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Base, Product, Review, User
from app.products import _public_product

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("provenance", ROOT / "alembic/versions/0011_product_provenance.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)
ROWS = json.loads(migration.SEED_FILE.read_text())["products"]


def test_published_snapshot_is_frozen_and_builder_uses_another_target():
    assert hashlib.sha256(migration.SEED_FILE.read_bytes()).hexdigest() == migration.SEED_SHA256
    builder = (ROOT / "scripts/build_catalog_seed.py").read_text()
    assert '/ "catalogo-candidate-v2.json"' in builder


def test_backfill_preserves_ownership_deletion_reviews_and_unknown_provenance():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        session = Session(connection)
        curator = User(public_name="Catalog", email="catalogo@merchant-app.invalid", password_hash="x")
        owner = User(public_name="Owner", email="owner@example.com", password_hash="x")
        session.add_all([curator, owner]); session.flush()
        products = []
        for index, row in enumerate(ROWS[:6]):
            product = Product(
                responsible_id=owner.id if index == 1 else curator.id,
                name=row["name"], brand=row["brand"], variant=row["variant"],
                quantity=row["quantity"], unit=row["unit"], category=row["category"],
                barcode=row["barcode"], identity_key=row["identity_key"],
                image_url="https://example.org/changed.jpg" if index == 2 else row.get("image_url"),
                deleted_at=datetime(2026, 1, 1) if index == 0 else None,
                source="Existing attribution" if index == 3 else None,
            )
            session.add(product); products.append(product)
        session.flush()
        review = Review(author_id=owner.id, product_id=products[0].id, repurchase_intent="yes", quality="high", expectation="met", value_for_money="good")
        session.add(review); session.flush()
        before = [(p.id, p.responsible_id, p.deleted_at, p.updated_at) for p in products]
        candidates = [dict(row) for row in ROWS[:6]]
        candidates[4]["source_url"] = "https://example.org/forged"
        candidates[5]["barcode"] = "0000000000000"
        assert migration.backfill(connection, candidates) == 1
        assert migration.backfill(connection, candidates) == 0
        session.expire_all()
        assert [(p.id, p.responsible_id, p.deleted_at, p.updated_at) for p in products] == before
        assert session.scalar(select(Review.id)) == review.id
        assert products[0].source == ROWS[0]["source"]
        assert _public_product(products[0]).source_url == ROWS[0]["source_url"]
        assert products[0].image_license_url is None
        assert [p.source for p in products[1:]] == [None, None, "Existing attribution", None, None]
        assert _public_product(products[1]).image_source is None


def test_postgres_upgrade_downgrade_and_reupgrade(monkeypatch):
    """Exercise actual ALTER TABLE/backfill on an isolated CI-only PG schema."""
    import os
    from uuid import uuid4

    import pytest
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect, text
    from sqlalchemy.engine import make_url

    url = os.getenv("TEST_DATABASE_URL")
    if not url or os.getenv("GITHUB_ACTIONS") != "true" or make_url(url).host not in {"127.0.0.1", "localhost"}:
        pytest.skip("PostgreSQL efêmero permitido somente no CI local")
    schema = f"provenance_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as conn:
            Base.metadata.create_all(conn)
            # Existing schema at 0010: all product fields except provenance.
            for name in migration.COLUMNS:
                conn.execute(text(f'ALTER TABLE produtos DROP COLUMN {name}'))
            legacy_spec = importlib.util.spec_from_file_location("legacy_seed", ROOT / "alembic/versions/0010_catalog_seed.py")
            legacy = importlib.util.module_from_spec(legacy_spec)
            legacy_spec.loader.exec_module(legacy)
            assert legacy.seed(conn, ROWS[:2]) == 2
            before = conn.execute(text("SELECT id, criador_id, excluido_em, atualizado_em FROM produtos ORDER BY id")).all()
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
            migration.upgrade()
            assert conn.execute(text("SELECT count(*) FROM produtos WHERE source IS NOT NULL")).scalar_one() == 2
            assert conn.execute(text("SELECT id, criador_id, excluido_em, atualizado_em FROM produtos ORDER BY id")).all() == before
            migration.downgrade()
            assert not set(migration.COLUMNS) & {c["name"] for c in inspect(conn).get_columns("produtos")}
            migration.upgrade()
            assert conn.execute(text("SELECT count(*) FROM produtos WHERE source IS NOT NULL")).scalar_one() == 2
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
