from decimal import Decimal

import pytest

from app.validation import (
    build_identity_key,
    normalize_quantity,
    normalize_text,
    normalize_variant,
    validate_comment,
    validate_gtin,
    validate_review_reasons,
)


@pytest.mark.parametrize(
    ("value", "unit", "expected", "expected_unit"),
    [
        ("1,5", "L", Decimal("1500.0"), "ml"),
        ("2", "kg", Decimal("2000"), "g"),
        ("6", "UN", Decimal("6"), "un"),
    ],
)
def test_quantity_is_converted_to_canonical_unit(value, unit, expected, expected_unit):
    result = normalize_quantity(value, unit)
    assert result.value == expected
    assert result.unit == expected_unit


@pytest.mark.parametrize("value,unit", [("0", "g"), ("1.0001", "kg"), ("1.5", "un")])
def test_quantity_rejects_invalid_values(value, unit):
    with pytest.raises(ValueError):
        normalize_quantity(value, unit)


def test_quantity_rejects_values_that_do_not_fit_numeric_column():
    normalize_quantity("99999999999999999.999", "g")
    with pytest.raises(ValueError):
        normalize_quantity("99999999999999999.999", "kg")


def test_text_preserves_accents_but_normalizes_spaces():
    assert normalize_text("  Pão   de Açúcar ", field="name", maximum=120) == "Pão de Açúcar"
    assert normalize_variant("  ") is None


@pytest.mark.parametrize("barcode", ["4006381333931", "7891000100103", "96385074"])
def test_valid_gtin_is_accepted(barcode):
    assert validate_gtin(barcode) == barcode


@pytest.mark.parametrize("barcode", ["4006381333932", "123", "abc12345", "00000000"])
def test_invalid_gtin_is_rejected(barcode):
    with pytest.raises(ValueError):
        validate_gtin(barcode)


def test_identity_key_is_unambiguous_and_uses_normalized_values():
    key = build_identity_key(
        name="Pão de Açúcar",
        brand="Ypê",
        variant="Capim-limão",
        quantity=Decimal("1500.0"),
        unit="ml",
    )
    assert key == '["pao de acucar","ype","capim-limao","1500","ml"]'


def test_integer_quantity_keeps_significant_trailing_zeroes():
    product_1500 = build_identity_key(
        name="Produto",
        brand="Marca",
        variant=None,
        quantity=Decimal("1500"),
        unit="g",
    )
    product_15 = build_identity_key(
        name="Produto",
        brand="Marca",
        variant=None,
        quantity=Decimal("15"),
        unit="g",
    )
    assert product_1500.endswith('"1500","g"]')
    assert product_1500 != product_15


def test_comment_is_trimmed_and_empty_comment_becomes_none():
    assert validate_comment("  compraria   novamente  ") == "compraria novamente"
    assert validate_comment("   ") is None


def test_comment_limit_is_enforced():
    with pytest.raises(ValueError):
        validate_comment("x" * 1001)


def test_review_requires_unique_valid_reason_and_comment_for_other():
    validate_review_reasons([("taste", "positive")], None)
    with pytest.raises(ValueError):
        validate_review_reasons([], None)
    with pytest.raises(ValueError):
        validate_review_reasons([("taste", "positive"), ("taste", "negative")], None)
    with pytest.raises(ValueError):
        validate_review_reasons([("other", "negative")], None)
    validate_review_reasons([("other", "negative")], " embalagem estranha ")
