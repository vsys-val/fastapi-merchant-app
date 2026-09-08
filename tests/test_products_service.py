from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.errors import ApiError
from app.models import Base, Product, Review, User
from app.products import (
    _is_product_uniqueness_error,
    create_product,
    delete_product,
    update_product,
)
from app.schemas import ProductCreate, ProductPatch


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
def users(session):
    owner = User(public_name="Valério", email="owner@example.com", password_hash="hash")
    other = User(public_name="Outra pessoa", email="other@example.com", password_hash="hash")
    session.add_all([owner, other])
    session.commit()
    return owner, other


def product_payload(**changes):
    values = {
        "name": "Café torrado",
        "brand": "Marca X",
        "variant": None,
        "quantity": "500",
        "unit": "g",
        "category": "food",
        "barcode": None,
    }
    values.update(changes)
    return ProductCreate(**values)


def add_review(session, product_id, author_id):
    review = Review(
        author_id=author_id,
        product_id=product_id,
        repurchase_intent="yes",
        quality="high",
        expectation="met",
        value_for_money="good",
    )
    session.add(review)
    session.commit()
    return review


class FakeDatabaseError(Exception):
    def __init__(self, sqlstate, constraint_name):
        self.sqlstate = sqlstate
        self.diag = type("Diagnostic", (), {"constraint_name": constraint_name})()


@pytest.mark.parametrize(
    "constraint_name",
    ["produtos_codigo_barras_key", "produtos_chave_identidade_key"],
)
def test_only_expected_product_unique_violations_are_classified(constraint_name):
    expected = FakeDatabaseError("23505", constraint_name)
    error = IntegrityError("statement", {}, expected)
    assert _is_product_uniqueness_error(error)


@pytest.mark.parametrize(
    ("sqlstate", "constraint_name"),
    [
        ("23503", "produtos_criador_id_fkey"),
        ("23505", "usuarios_email_key"),
        (None, None),
    ],
)
def test_unrelated_integrity_errors_are_not_disguised_as_product_conflicts(
    sqlstate, constraint_name
):
    unexpected = FakeDatabaseError(sqlstate, constraint_name)
    error = IntegrityError("statement", {}, unexpected)
    assert not _is_product_uniqueness_error(error)


def test_create_product_returns_canonical_public_representation(session, users):
    owner, _ = users
    result = create_product(
        product_payload(quantity="1,5", unit="kg", barcode="7891000100103"),
        owner,
        session,
    )
    assert result.created
    assert result.product.model_dump(mode="json") == {
        "id": 1,
        "name": "Café torrado",
        "brand": "Marca X",
        "variant": None,
        "quantity": 1500,
        "unit": "g",
        "category": "food",
        "barcode": "7891000100103",
    }


def test_active_duplicate_conflicts_with_existing_id(session, users):
    owner, _ = users
    original = create_product(product_payload(), owner, session)
    with pytest.raises(ApiError) as caught:
        create_product(
            product_payload(name=" CAFE   TORRADO ", brand="marca x"),
            owner,
            session,
        )
    assert caught.value.status_code == 409
    assert caught.value.details == {"existing_product_id": original.product.id}


def test_barcode_and_identity_pointing_to_different_rows_is_ambiguous(session, users):
    owner, _ = users
    first = create_product(
        product_payload(name="Produto A", barcode="7891000100103"), owner, session
    )
    second = create_product(product_payload(name="Produto B"), owner, session)

    with pytest.raises(ApiError) as caught:
        create_product(
            product_payload(name="Produto B", barcode="7891000100103"),
            owner,
            session,
        )
    assert caught.value.status_code == 409
    assert caught.value.details is None
    assert session.get(Product, first.product.id).name == "Produto A"
    assert session.get(Product, second.product.id).barcode is None


def test_deleted_product_is_reactivated_with_same_id_and_new_owner(session, users):
    owner, other = users
    original = create_product(product_payload(), owner, session)
    stored = session.get(Product, original.product.id)
    created_at = stored.created_at
    delete_product(stored.id, owner, session)

    result = create_product(
        product_payload(name="CAFE TORRADO", brand="marca x", category="other"),
        other,
        session,
    )
    reactivated = session.get(Product, stored.id)
    assert not result.created
    assert result.product.id == original.product.id
    assert reactivated.responsible_id == other.id
    assert reactivated.deleted_at is None
    assert reactivated.created_at == created_at
    assert reactivated.category == "other"


def test_inactive_product_with_legacy_review_is_not_reactivated(session, users):
    owner, other = users
    original = create_product(product_payload(), owner, session)
    stored = session.get(Product, original.product.id)
    stored.deleted_at = datetime.now(timezone.utc)
    session.commit()
    add_review(session, stored.id, owner.id)

    with pytest.raises(ApiError) as caught:
        create_product(product_payload(), other, session)
    assert caught.value.status_code == 409
    assert session.get(Product, stored.id).deleted_at is not None


def test_patch_merges_fields_and_allows_owners_own_review(session, users):
    owner, _ = users
    created = create_product(product_payload(), owner, session)
    add_review(session, created.product.id, owner.id)

    updated = update_product(
        created.product.id,
        ProductPatch(brand="Marca Nova", variant=" Tradicional ", quantity="750"),
        owner,
        session,
    )
    assert updated.brand == "Marca Nova"
    assert updated.variant == "Tradicional"
    assert updated.quantity == 750
    assert updated.unit == "g"
    assert updated.name == "Café torrado"


def test_patch_by_other_user_is_forbidden_before_review_check(session, users):
    owner, other = users
    created = create_product(product_payload(), owner, session)
    add_review(session, created.product.id, other.id)
    with pytest.raises(ApiError) as caught:
        update_product(created.product.id, ProductPatch(brand="Outra"), other, session)
    assert caught.value.status_code == 403


def test_patch_is_blocked_by_another_authors_review(session, users):
    owner, other = users
    created = create_product(product_payload(), owner, session)
    add_review(session, created.product.id, other.id)
    with pytest.raises(ApiError) as caught:
        update_product(created.product.id, ProductPatch(brand="Nova marca"), owner, session)
    assert caught.value.status_code == 409
    assert caught.value.code == "product_locked_by_reviews"


def test_patch_that_creates_duplicate_preserves_original(session, users):
    owner, _ = users
    first = create_product(product_payload(name="Produto A"), owner, session)
    second = create_product(product_payload(name="Produto B"), owner, session)

    with pytest.raises(ApiError) as caught:
        update_product(
            first.product.id,
            ProductPatch(name="Produto B"),
            owner,
            session,
        )
    assert caught.value.status_code == 409
    assert session.get(Product, first.product.id).name == "Produto A"
    assert session.get(Product, second.product.id).name == "Produto B"


def test_delete_is_logical_and_repeated_delete_returns_not_found(session, users):
    owner, _ = users
    created = create_product(product_payload(), owner, session)
    delete_product(created.product.id, owner, session)
    assert session.get(Product, created.product.id).deleted_at is not None

    with pytest.raises(ApiError) as caught:
        delete_product(created.product.id, owner, session)
    assert caught.value.status_code == 404


def test_delete_rejects_other_owner_and_any_review(session, users):
    owner, other = users
    created = create_product(product_payload(), owner, session)
    with pytest.raises(ApiError) as forbidden:
        delete_product(created.product.id, other, session)
    assert forbidden.value.status_code == 403

    add_review(session, created.product.id, owner.id)
    with pytest.raises(ApiError) as conflict:
        delete_product(created.product.id, owner, session)
    assert conflict.value.status_code == 409
    assert session.get(Product, created.product.id).deleted_at is None
