from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.errors import ApiError
from app.models import Base, Product, Review, ReviewReason, User
from app.products import create_product, delete_product
from app.reviews import (
    _is_review_uniqueness_error,
    create_review,
    delete_review,
    update_review,
)
from app.schemas import ProductCreate, ReviewCreate, ReviewPatch


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database_session:
        yield database_session
    Base.metadata.drop_all(engine)


@pytest.fixture
def context(session):
    owner = User(public_name="Valério", email="owner@example.com", password_hash="hash")
    other = User(public_name="Outra pessoa", email="other@example.com", password_hash="hash")
    session.add_all([owner, other])
    session.commit()
    product = create_product(
        ProductCreate(
            name="Café torrado",
            brand="Marca X",
            quantity=500,
            unit="g",
            category="food",
        ),
        owner,
        session,
    ).product
    return owner, other, product


def review_payload(**changes):
    values = {
        "repurchase_intent": "yes",
        "quality": "high",
        "expectation": "met",
        "value_for_money": "good",
        "reasons": [{"aspect": "taste", "perception": "positive"}],
        "comment": "Compraria novamente.",
    }
    values.update(changes)
    return ReviewCreate(**values)


def test_create_review_persists_complete_public_result(session, context):
    owner, _, product = context
    result = create_review(product.id, review_payload(), owner, session)
    assert result.id > 0
    assert result.repurchase_intent == "yes"
    assert result.reasons[0].model_dump() == {
        "aspect": "taste",
        "perception": "positive",
    }
    assert result.created_at == result.updated_at
    assert session.scalar(select(ReviewReason.id)) is not None


def test_duplicate_review_returns_existing_id(session, context):
    owner, _, product = context
    first = create_review(product.id, review_payload(), owner, session)
    with pytest.raises(ApiError) as caught:
        create_review(product.id, review_payload(), owner, session)
    assert caught.value.status_code == 409
    assert caught.value.details == {"existing_review_id": first.id}
    assert session.query(Review).count() == 1


def test_inactive_or_missing_product_is_not_reviewable(session, context):
    owner, _, product = context
    delete_product(product.id, owner, session)
    for product_id in (product.id, 999_999):
        with pytest.raises(ApiError) as caught:
            create_review(product_id, review_payload(), owner, session)
        assert caught.value.status_code == 404


def test_patch_merges_scalars_and_preserves_omitted_reasons(session, context):
    owner, _, product = context
    created = create_review(product.id, review_payload(), owner, session)
    stored = session.get(Review, created.id)
    created_at = stored.created_at
    updated = update_review(created.id, ReviewPatch(quality="adequate"), owner, session)
    assert updated.quality == "adequate"
    assert updated.repurchase_intent == "yes"
    assert updated.reasons[0].aspect == "taste"
    assert updated.created_at == created_at
    assert updated.updated_at >= created_at


def test_patch_replaces_reason_list_without_transient_unique_conflict(session, context):
    owner, _, product = context
    created = create_review(product.id, review_payload(), owner, session)
    updated = update_review(
        created.id,
        ReviewPatch(
            reasons=[
                {"aspect": "taste", "perception": "negative"},
                {"aspect": "price", "perception": "positive"},
            ]
        ),
        owner,
        session,
    )
    assert [(reason.aspect, reason.perception) for reason in updated.reasons] == [
        ("taste", "negative"),
        ("price", "positive"),
    ]
    assert session.query(ReviewReason).count() == 2


def test_patch_validates_the_merged_other_comment_rule(session, context):
    owner, _, product = context
    created = create_review(
        product.id,
        review_payload(comment=None),
        owner,
        session,
    )
    with pytest.raises(ApiError) as caught:
        update_review(
            created.id,
            ReviewPatch(reasons=[{"aspect": "other", "perception": "negative"}]),
            owner,
            session,
        )
    assert caught.value.status_code == 422
    unchanged = session.get(Review, created.id)
    assert unchanged.comment is None
    assert unchanged.reasons[0].aspect == "taste"


def test_patch_can_use_existing_comment_but_cannot_remove_it_from_other(session, context):
    owner, _, product = context
    created = create_review(product.id, review_payload(), owner, session)
    updated = update_review(
        created.id,
        ReviewPatch(reasons=[{"aspect": "other", "perception": "positive"}]),
        owner,
        session,
    )
    assert updated.reasons[0].aspect == "other"
    with pytest.raises(ApiError) as caught:
        update_review(created.id, ReviewPatch(comment=None), owner, session)
    assert caught.value.status_code == 422
    session.refresh(session.get(Review, created.id))
    assert session.get(Review, created.id).comment == "Compraria novamente."


def test_patch_checks_not_found_before_authorship(session, context):
    owner, other, product = context
    created = create_review(product.id, review_payload(), owner, session)
    with pytest.raises(ApiError) as forbidden:
        update_review(created.id, ReviewPatch(quality="low"), other, session)
    assert forbidden.value.status_code == 403
    with pytest.raises(ApiError) as missing:
        update_review(999_999, ReviewPatch(quality="low"), other, session)
    assert missing.value.status_code == 404


def test_delete_review_is_physical_cascades_and_is_author_only(session, context):
    owner, other, product = context
    created = create_review(product.id, review_payload(), owner, session)
    with pytest.raises(ApiError) as forbidden:
        delete_review(created.id, other, session)
    assert forbidden.value.status_code == 403
    delete_review(created.id, owner, session)
    assert session.get(Review, created.id) is None
    assert session.query(ReviewReason).count() == 0
    with pytest.raises(ApiError) as repeated:
        delete_review(created.id, owner, session)
    assert repeated.value.status_code == 404


class FakeDatabaseError(Exception):
    def __init__(self, sqlstate, constraint_name):
        self.sqlstate = sqlstate
        self.diag = type("Diagnostic", (), {"constraint_name": constraint_name})()


@pytest.mark.parametrize(
    ("sqlstate", "constraint_name", "expected"),
    [
        ("23505", "uq_avaliacoes_usuario_produto", True),
        ("23505", "uq_motivos_avaliacao_aspecto", False),
        ("23503", "avaliacoes_produto_id_fkey", False),
    ],
)
def test_only_review_identity_unique_violation_becomes_conflict(
    sqlstate, constraint_name, expected
):
    original = FakeDatabaseError(sqlstate, constraint_name)
    error = IntegrityError("statement", {}, original)
    assert _is_review_uniqueness_error(error) is expected
