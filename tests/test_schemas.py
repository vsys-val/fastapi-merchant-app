from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import ProductCreate, ProductPatch, ReviewCreate, ReviewPatch


def test_product_create_returns_canonical_values():
    product = ProductCreate(
        name=" Pão   de Açúcar ",
        brand="Ypê",
        variant=" ",
        quantity="1,5",
        unit="L",
        category="cleaning",
        barcode="7891000100103",
    )
    assert product.name == "Pão de Açúcar"
    assert product.variant is None
    assert product.quantity == Decimal("1500.0")
    assert product.unit == "ml"


def test_product_patch_distinguishes_omitted_from_null():
    omitted = ProductPatch(brand="Nova marca")
    removed = ProductPatch(variant=None, barcode=None)
    assert omitted.model_fields_set == {"brand"}
    assert removed.model_fields_set == {"variant", "barcode"}


def test_product_patch_accepts_independent_quantity_and_unit_changes():
    assert ProductPatch(quantity="500").quantity == Decimal("500")
    assert ProductPatch(unit="G").unit == "g"
    with pytest.raises(ValidationError):
        ProductPatch(name=None)
    with pytest.raises(ValidationError):
        ProductPatch(quantity=None)
    with pytest.raises(ValidationError):
        ProductPatch(unit=None)
    with pytest.raises(ValidationError):
        ProductPatch(category=None)
    with pytest.raises(ValidationError):
        ProductPatch(name="x")
    with pytest.raises(ValidationError):
        ProductPatch()


def test_review_create_requires_reason_and_other_comment():
    review = ReviewCreate(
        repurchase_intent="yes",
        quality="high",
        expectation="met",
        value_for_money="good",
        reasons=[{"aspect": "taste", "perception": "positive"}],
    )
    assert review.comment is None
    with pytest.raises(ValidationError):
        ReviewCreate(
            repurchase_intent="yes",
            quality="high",
            expectation="met",
            value_for_money="good",
            reasons=[{"aspect": "other", "perception": "negative"}],
        )


def test_review_patch_replaces_reasons_as_a_whole():
    patch = ReviewPatch(reasons=[{"aspect": "price", "perception": "negative"}])
    assert patch.model_fields_set == {"reasons"}
    with pytest.raises(ValidationError):
        ReviewPatch(reasons=[])
    with pytest.raises(ValidationError):
        ReviewPatch()
    with pytest.raises(ValidationError):
        ReviewPatch(quality=None)


def test_review_patch_can_keep_existing_comment_for_other_reason():
    patch = ReviewPatch(reasons=[{"aspect": "other", "perception": "negative"}])
    assert patch.comment is None
    assert "comment" not in patch.model_fields_set
    with pytest.raises(ValidationError):
        ReviewPatch(
            reasons=[{"aspect": "other", "perception": "negative"}],
            comment=None,
        )


def test_review_reasons_are_limited_to_the_number_of_distinct_aspects():
    reasons = [{"aspect": "taste", "perception": "positive"}] * 13
    with pytest.raises(ValidationError):
        ReviewCreate(
            repurchase_intent="yes",
            quality="high",
            expectation="met",
            value_for_money="good",
            reasons=reasons,
        )
