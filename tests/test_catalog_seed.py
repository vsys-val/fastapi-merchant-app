"""Catálogo inicial: conversão do Open Food Facts, arquivo versionado e migração 0009."""

import importlib.util
import json
import os
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import CATALOG_CURATOR_EMAIL, Base, Product, Review, User
from app.schemas import ProductCreate
from app.validation import build_identity_key, identity_text

ROOT = Path(__file__).resolve().parent.parent


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load(ROOT / "scripts" / "build_catalog_seed.py", "build_catalog_seed")
migration = _load(ROOT / "alembic" / "versions" / "0010_catalog_seed.py", "migration_0010")

OFF = builder.SOURCES[0]
OBF = builder.SOURCES[1]
OPF = builder.SOURCES[2]


def _off(**overrides):
    product = {
        "code": "7891000100103",
        "product_name_pt": "BISCOITO RECHEADO DE CHOCOLATE 140g",
        "brands": "NESTLÉ,Nestlé Brasil",
        "quantity": "140 g",
        "product_quantity": "140",
        "product_quantity_unit": "g",
        "categories_tags": ["en:snacks", "en:biscuits"],
        "unique_scans_n": 50,
    }
    product.update(overrides)
    return product


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://images.openfoodfacts.org/images/products/789/100/010/0103/front_pt.12.400.jpg", True),
        ("https://images.openbeautyfacts.org/images/products/789/100/010/0103/front_pt.3.400.jpg", True),
        ("http://images.openfoodfacts.org/images/products/789/100/010/0103/front_pt.12.400.jpg", False),
        ("https://example.com/images/products/789/front_pt.12.400.jpg", False),
        ("https://images.openfoodfacts.org/images/products/789/front_pt.12.full.jpg", False),
        ("", False),
    ],
)
def test_keeps_only_front_photos_from_the_open_food_facts_image_servers(url, expected):
    row = builder.to_seed_row(OFF, _off(image_front_url=url))
    assert (row["image_url"] == url) is expected
    assert row["image_url"] is None or expected


def test_converts_an_open_food_facts_product_with_the_api_rules():
    row = builder.to_seed_row(OFF, _off())
    assert row["name"] == "Biscoito Recheado de Chocolate"
    assert row["brand"] == "Nestlé"
    assert (row["quantity"], row["unit"], row["category"]) == ("140", "g", "food")
    assert row["barcode"] == "7891000100103"
    assert row["identity_key"] == build_identity_key(
        name=row["name"], brand=row["brand"], variant=None, quantity=Decimal("140"), unit="g"
    )
    assert row["search_name"] == "biscoito recheado de chocolate"
    assert row["source_url"] == "https://world.openfoodfacts.org/product/7891000100103"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"product_quantity": None, "quantity": "1,5 kg"}, ("1500", "g")),
        ({"product_quantity": None, "product_quantity_unit": None, "quantity": "2 L"}, ("2000", "ml")),
        ({"product_quantity": None, "quantity": "33 cl"}, ("330", "ml")),
        ({"product_quantity": None, "quantity": "12 unidades"}, ("12", "un")),
    ],
)
def test_reads_the_quantity_text_when_the_structured_field_is_missing(overrides, expected):
    row = builder.to_seed_row(OFF, _off(**overrides))
    assert (row["quantity"], row["unit"]) == expected


@pytest.mark.parametrize(
    "overrides",
    [
        {"quantity": "6 x 200 ml", "product_quantity": "1200", "product_quantity_unit": "ml"},
        {"product_quantity": None, "quantity": "pacote"},
        {"code": "7891000100104"},  # dígito verificador errado
        {"brands": ""},
        {"product_name_pt": "", "product_name": ""},
        {"product_name_pt": "Nestlé"},  # nome igual à marca
    ],
    ids=["multipack", "sem-quantidade", "gtin-invalido", "sem-marca", "sem-nome", "nome-igual-marca"],
)
def test_rejects_products_the_api_would_refuse_or_that_are_ambiguous(overrides):
    assert builder.to_seed_row(OFF, _off(**overrides)) is None


@pytest.mark.parametrize(
    ("source", "tags", "name", "unit", "expected"),
    [
        (OFF, ["en:beverages", "en:sodas"], "Sabor Laranja", "ml", "beverages"),
        (OFF, ["en:snacks"], "Guaraná Antarctica Lata", "ml", "beverages"),
        (OFF, ["en:beverages"], "Leite em Pó Integral", "g", "food"),
        (OFF, ["en:snacks"], "Biscoito Recheado", "g", "food"),
        (OBF, [], "Creme Dental", "g", "personal_hygiene"),
        (OPF, [], "Lava Louças Neutro", "ml", "cleaning"),
        (OPF, [], "Amaciante de Roupas", "ml", "cleaning"),
        (OPF, [], "Filtro de Papel 102", "un", "household_utilities"),
        (OPF, [], "Livro de História", "un", None),
        (OFF, [], "Wafer Choc C/avela", "g", "food"),
        (OFF, [], "Açúcar Refinado Caravelas", "g", "food"),
        (OBF, [], "Água de Colônia sem Álcool", "ml", "personal_hygiene"),
        (OBF, [], "Álcool em Gel 70", "g", "cleaning"),
        (OFF, [], "Matte Leão Original", "g", "beverages"),
    ],
)
def test_categories_come_from_the_name_first_then_the_source(source, tags, name, unit, expected):
    assert builder.category_of(source, tags, name, unit) == expected


@pytest.mark.parametrize(
    ("raw", "brand", "expected"),
    [
        ("Leite Condensado Moça", "Nestlé", "Leite Condensado Moça"),
        ("ARROZ TIPO 1 E FEIJÃO", "Tio João", "Arroz Tipo 1 e Feijão"),
        ("achocolatado em pó, NESCAU", "Nestlé", "Achocolatado em pó, Nescau"),
        ("YOKI Batata Palha Tradicional", "Yoki", "Batata Palha Tradicional"),
        ("Bacon - Torcida - Torcida", "Torcida", "Bacon"),
        ("Açúcar Demerara Orgânico (1 kg)", "Native", "Açúcar Demerara Orgânico"),
        ("Leite UHT Integral", "Italac", "Leite UHT Integral"),
    ],
)
def test_names_are_tidied_without_losing_information(raw, brand, expected):
    assert builder.clean_name(raw, brand) == expected


def test_lowercase_brands_get_initial_capitals():
    assert builder.clean_brand("coca cola") == "Coca Cola"
    assert builder.clean_brand("NESTLÉ,Nestlé Brasil") == "Nestlé"
    assert builder.clean_brand("Hershey's") == "Hershey's"


@pytest.mark.parametrize(
    "overrides",
    [
        {"product_name_pt": "predilecta"},
        {"product_name_pt": "Nivea", "brands": "loção hidratante"},
    ],
    ids=["nome-de-uma-palavra-minusculo", "marca-generica"],
)
def test_rejects_incomplete_source_data(overrides):
    assert builder.to_seed_row(OFF, _off(**overrides)) is None


def test_drops_products_whose_brand_was_swapped_at_the_source():
    def row(name, brand):
        return {"search_name": identity_text(name), "search_brand": identity_text(brand)}

    kept, dropped = builder.drop_brand_conflicts({
        "beverages": [
            row("Água de Coco Sococo Caixa", "Kellogg's"),  # marca trocada
            row("Água de Coco Integral", "Sococo"),
            row("Nescau Lata", "Nestlé"),  # submarca: a Nestlé se repete
            row("Leite Ninho", "Nestlé"),
        ],
    })
    assert dropped == 1
    assert [r["search_brand"] for r in kept["beverages"]] == ["sococo", "nestle", "nestle"]


# O arquivo versionado precisa continuar válido para a API atual.

SEED = json.loads((ROOT / "data" / "catalogo-inicial.json").read_text(encoding="utf-8"))


def test_seed_file_carries_the_odbl_attribution():
    assert SEED["license"] == "ODbL-1.0"
    assert "Open Food Facts" in SEED["attribution"]


def test_seed_file_has_about_500_unique_products_in_several_categories():
    products = SEED["products"]
    assert 400 <= len(products) <= 550
    assert len({row["identity_key"] for row in products}) == len(products)
    codes = [row["barcode"] for row in products if row["barcode"]]
    assert len(set(codes)) == len(codes)
    categories = Counter(row["category"] for row in products)
    assert {"food", "beverages"} <= set(categories)


def test_every_seed_row_passes_the_api_rules_and_matches_its_derived_fields():
    for row in SEED["products"]:
        payload = ProductCreate(
            name=row["name"], brand=row["brand"], variant=row["variant"],
            quantity=row["quantity"], unit=row["unit"], category=row["category"], barcode=row["barcode"],
        )
        assert (payload.name, payload.brand, payload.unit) == (row["name"], row["brand"], row["unit"])
        assert payload.quantity == Decimal(row["quantity"])
        assert row["identity_key"] == build_identity_key(
            name=payload.name, brand=payload.brand, variant=payload.variant,
            quantity=payload.quantity, unit=payload.unit,
        )
        assert (row["search_name"], row["search_brand"]) == (identity_text(payload.name), identity_text(payload.brand))
        assert row.get("image_url") is None or builder.IMAGE_URL.match(row["image_url"])


# Migração no PostgreSQL efêmero do CI.


@pytest.fixture
def connection():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL não foi definido")
    if os.getenv("GITHUB_ACTIONS") != "true" or make_url(database_url).host not in {"127.0.0.1", "localhost"}:
        pytest.skip("teste destrutivo permitido apenas no PostgreSQL efêmero do GitHub Actions")
    admin_engine = create_engine(database_url)
    schema = f"seed_{uuid4().hex}"
    with admin_engine.begin() as setup:
        setup.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    try:
        with engine.begin() as conn:
            yield conn
    finally:
        engine.dispose()
        with admin_engine.begin() as cleanup:
            cleanup.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_migration_inserts_once_skips_existing_products_and_reverts_only_unreviewed(connection):
    products = SEED["products"][:5]
    session = Session(bind=connection)
    ana = User(public_name="Ana", email="ana@example.com", password_hash="x")
    session.add(ana)
    session.flush()
    # Ana já cadastrou o primeiro produto: a migração não duplica nem toma posse dele.
    first = products[0]
    session.add(Product(
        responsible_id=ana.id, name=first["name"], brand=first["brand"], variant=first["variant"],
        quantity=Decimal(first["quantity"]), unit=first["unit"], category=first["category"],
        barcode=first["barcode"], identity_key=first["identity_key"],
    ))
    session.flush()

    assert migration.seed(connection, products) == 4
    assert migration.seed(connection, products) == 0

    curator = session.scalars(select(User).where(User.email == CATALOG_CURATOR_EMAIL)).one()
    assert curator.public_name == "Catálogo Merchant"
    assert curator.email_verified_at is not None
    assert curator.password_hash.startswith("$argon2")
    owners = dict(session.execute(select(Product.identity_key, Product.responsible_id)).all())
    assert owners[first["identity_key"]] == ana.id
    assert sum(owner == curator.id for owner in owners.values()) == 4

    reviewed = session.scalars(select(Product).where(Product.identity_key == products[1]["identity_key"])).one()
    session.add(Review(author_id=ana.id, product_id=reviewed.id, repurchase_intent="yes", quality="high", expectation="met", value_for_money="good"))
    session.flush()

    migration.unseed(connection)
    remaining = set(session.scalars(select(Product.identity_key)).all())
    assert remaining == {first["identity_key"], products[1]["identity_key"]}
    # A conta fica enquanto tiver produto avaliado.
    assert session.scalar(select(User.id).where(User.email == CATALOG_CURATOR_EMAIL)) == curator.id
