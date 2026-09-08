import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.catalog import (
    get_product_detail,
    list_community_reviews,
    list_own_products,
    list_own_reviews,
    search_products,
)
from app.errors import ApiError
from app.models import Base, Product, User
from app.products import create_product, delete_product
from app.reviews import create_review
from app.schemas import ProductCreate, ReviewCreate


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database_session:
        yield database_session
    Base.metadata.drop_all(engine)


@pytest.fixture
def catalog(session):
    users = [
        User(public_name="Valério", email="valerio@example.com", password_hash="hash"),
        User(public_name="Ana", email="ana@example.com", password_hash="hash"),
        User(public_name="Beto", email="beto@example.com", password_hash="hash"),
    ]
    session.add_all(users)
    session.commit()

    def product(name, brand, category="food", barcode=None):
        return create_product(
            ProductCreate(
                name=name,
                brand=brand,
                quantity=500,
                unit="g",
                category=category,
                barcode=barcode,
            ),
            users[0],
            session,
        ).product

    products = [
        product("Açaí tradicional", "Sabor Brasil", "food", "7891000100103"),
        product("Arroz integral", "Grão Bom"),
        product("Sabão líquido", "Limpeza Já", "cleaning"),
        product("Produto removido", "Marca Antiga"),
    ]
    delete_product(products[3].id, users[0], session)
    return users, products


def review_payload(intent, quality="high", expectation="met", value="good"):
    return ReviewCreate(
        repurchase_intent=intent,
        quality=quality,
        expectation=expectation,
        value_for_money=value,
        reasons=[{"aspect": "taste", "perception": "positive"}],
    )


def search(session, user=None, **changes):
    values = {
        "current_user": user,
        "name": None,
        "brand": None,
        "category": None,
        "barcode": None,
        "page": 1,
        "page_size": 20,
    }
    values.update(changes)
    return search_products(session, **values)


def test_search_is_accent_insensitive_combines_filters_and_hides_inactive(session, catalog):
    _, products = catalog
    result = search(session, name="acai", brand="sabor", category="food")
    assert result.total == 1
    assert result.items[0].id == products[0].id
    all_products = search(session)
    assert all_products.total == 3
    assert [item.name for item in all_products.items] == [
        "Açaí tradicional",
        "Arroz integral",
        "Sabão líquido",
    ]


def test_search_barcode_is_exact_isolated_and_pagination_is_stable(session, catalog):
    _, products = catalog
    found = search(session, barcode="7891000100103", page_size=1)
    assert found.total == 1
    assert found.items[0].id == products[0].id
    second_page = search(session, page=2, page_size=2)
    assert second_page.total == 3
    assert [item.name for item in second_page.items] == ["Sabão líquido"]
    with pytest.raises(ApiError) as combined:
        search(session, barcode="7891000100103", name="açaí")
    assert combined.value.status_code == 422


def test_list_summary_separates_own_review_from_community(session, catalog):
    users, products = catalog
    create_review(products[0].id, review_payload("yes"), users[0], session)
    create_review(products[0].id, review_payload("no", "low", "not_met", "poor"), users[1], session)

    visitor = search(session, name="açaí").items[0]
    assert visitor.community_summary.total_reviews == 2
    assert visitor.community_summary.repurchase_intent.yes == 50.0
    assert visitor.your_repurchase_intent is None

    authenticated = search(session, users[0], name="açaí").items[0]
    assert authenticated.community_summary.total_reviews == 1
    assert authenticated.community_summary.repurchase_intent.no == 100.0
    assert authenticated.your_repurchase_intent == "yes"


def test_empty_community_uses_zero_for_every_distribution(session, catalog):
    _, products = catalog
    detail = get_product_detail(session, products[1].id, None)
    assert detail.community_summary.total_reviews == 0
    assert set(detail.community_summary.repurchase_intent.model_dump().values()) == {0.0}
    assert set(detail.community_summary.quality.model_dump().values()) == {0.0}
    assert set(detail.community_summary.expectation.model_dump().values()) == {0.0}
    assert set(detail.community_summary.value_for_money.model_dump().values()) == {0.0}


def test_detail_has_full_distributions_and_own_review(session, catalog):
    users, products = catalog
    create_review(products[0].id, review_payload("yes"), users[0], session)
    create_review(products[0].id, review_payload("maybe", "adequate", "exceeded", "fair"), users[1], session)
    create_review(products[0].id, review_payload("no", "low", "not_met", "poor"), users[2], session)

    visitor = get_product_detail(session, products[0].id, None)
    assert visitor.community_summary.total_reviews == 3
    assert visitor.community_summary.repurchase_intent.model_dump() == {
        "yes": 33.3,
        "maybe": 33.3,
        "no": 33.3,
    }
    assert sum(visitor.community_summary.repurchase_intent.model_dump().values()) == pytest.approx(99.9)
    assert visitor.community_summary.quality.adequate == 33.3
    assert visitor.your_review is None

    owner = get_product_detail(session, products[0].id, users[0])
    assert owner.community_summary.total_reviews == 2
    assert owner.your_review.repurchase_intent == "yes"
    assert owner.community_summary.repurchase_intent.yes == 0.0


def test_community_reviews_are_private_paginated_and_exclude_current_user(session, catalog):
    users, products = catalog
    own = create_review(products[0].id, review_payload("yes"), users[0], session)
    other = create_review(products[0].id, review_payload("no"), users[1], session)
    page = list_community_reviews(session, products[0].id, users[0], 1, 1)
    assert page.total == 1
    assert page.items[0].id == other.id
    assert page.items[0].author_name == "Ana"
    assert "author_id" not in page.items[0].model_dump()
    assert "email" not in page.items[0].model_dump()
    visitor = list_community_reviews(session, products[0].id, None, 1, 20)
    assert visitor.total == 2
    assert {item.id for item in visitor.items} == {own.id, other.id}


def test_personal_lists_include_product_summary_and_only_active_responsibility(session, catalog):
    users, products = catalog
    created = create_review(products[1].id, review_payload("yes"), users[0], session)
    reviews = list_own_reviews(session, users[0], 1, 20)
    assert reviews.total == 1
    assert reviews.items[0].id == created.id
    assert reviews.items[0].product.id == products[1].id
    assert set(reviews.items[0].product.model_dump()) == {
        "id", "name", "brand", "variant", "quantity", "unit", "category", "barcode"
    }
    products_page = list_own_products(session, users[0], 1, 20)
    assert products_page.total == 3
    assert products[3].id not in {item.id for item in products_page.items}
    assert list_own_products(session, users[1], 1, 20).items == []


def test_inactive_or_missing_product_returns_not_found_in_reads(session, catalog):
    _, products = catalog
    for product_id in (products[3].id, 999_999):
        with pytest.raises(ApiError) as detail:
            get_product_detail(session, product_id, None)
        assert detail.value.status_code == 404
        with pytest.raises(ApiError) as reviews:
            list_community_reviews(session, product_id, None, 1, 20)
        assert reviews.value.status_code == 404
