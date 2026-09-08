"""Normalização e validações puras das entradas da API.

As funções deste módulo não acessam banco nem dependem do FastAPI. Isso deixa
as regras de negócio fáceis de testar antes de conectá-las aos endpoints.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Final


_WHITESPACE: Final = re.compile(r"\s+")
_ALLOWED_UNITS: Final = {"g", "kg", "ml", "L", "un"}
_UNIT_CONVERSION: Final = {
    "g": ("g", Decimal("1")),
    "kg": ("g", Decimal("1000")),
    "ml": ("ml", Decimal("1")),
    "L": ("ml", Decimal("1000")),
    "un": ("un", Decimal("1")),
}
_GTIN_LENGTHS: Final = {8, 12, 13, 14}
_REVIEW_ASPECTS: Final = {
    "taste",
    "fragrance",
    "texture_consistency",
    "effectiveness_performance",
    "quantity_yield",
    "ease_of_use_preparation",
    "packaging",
    "durability_preservation",
    "composition_ingredients",
    "safety_tolerance",
    "price",
    "other",
}


def normalize_text(value: str, *, field: str, maximum: int) -> str:
    """Normaliza espaços sem remover acentos ou alterar o texto exibido."""

    if not isinstance(value, str):
        raise ValueError(f"{field} deve ser texto.")
    normalized = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip()
    if not normalized:
        raise ValueError(f"{field} não pode ficar vazio.")
    if len(normalized) > maximum:
        raise ValueError(f"{field} deve ter no máximo {maximum} caracteres.")
    return normalized


def normalize_variant(value: str | None) -> str | None:
    """Variante vazia equivale a nulo, conforme o contrato do MVP."""

    if value is None:
        return None
    normalized = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip()
    return normalized or None


def normalize_unit(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("unit deve ser texto.")
    candidate = value.strip()
    if candidate.lower() == "l":
        candidate = "L"
    else:
        candidate = candidate.lower()
    if candidate not in _ALLOWED_UNITS:
        raise ValueError("unit deve ser uma de: g, kg, ml, L ou un.")
    return candidate


def parse_quantity(value: Decimal | int | float | str) -> Decimal:
    """Converte decimal brasileiro ou internacional sem aceitar infinitos."""

    if isinstance(value, bool):
        raise ValueError("quantity deve ser numérica.")
    try:
        quantity = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError("quantity deve ser um número válido.") from None
    if not quantity.is_finite() or quantity <= 0:
        raise ValueError("quantity deve ser maior que zero e finita.")
    if max(0, -quantity.normalize().as_tuple().exponent) > 3:
        raise ValueError("quantity pode ter no máximo três casas decimais.")
    return quantity


@dataclass(frozen=True, slots=True)
class NormalizedQuantity:
    value: Decimal
    unit: str


def normalize_quantity(value: Decimal | int | float | str, unit: str) -> NormalizedQuantity:
    source_unit = normalize_unit(unit)
    quantity = parse_quantity(value)
    canonical_unit, factor = _UNIT_CONVERSION[source_unit]
    normalized = quantity * factor
    if max(0, -normalized.normalize().as_tuple().exponent) > 3:
        raise ValueError("quantity pode ter no máximo três casas decimais.")
    if canonical_unit == "un" and normalized != normalized.to_integral_value():
        raise ValueError("quantity em unidades deve ser um número inteiro.")
    return NormalizedQuantity(normalized, canonical_unit)


def _without_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def identity_text(value: str | None) -> str:
    """Forma estável para comparar identidades sem alterar o texto público."""

    if value is None:
        return ""
    return _WHITESPACE.sub(" ", _without_accents(value).casefold()).strip()


def decimal_text(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def build_identity_key(
    *, name: str, brand: str, variant: str | None, quantity: Decimal, unit: str
) -> str:
    """Serializa a tupla normalizada sem ambiguidades nem separadores frágeis."""

    values = [
        identity_text(name),
        identity_text(brand),
        identity_text(variant),
        decimal_text(quantity),
        unit,
    ]
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def validate_gtin(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.isdigit():
        raise ValueError("barcode deve conter somente números.")
    if len(value) not in _GTIN_LENGTHS or not any(digit != "0" for digit in value):
        raise ValueError("barcode deve ser um GTIN-8, GTIN-12, GTIN-13 ou GTIN-14.")
    digits = [int(digit) for digit in value]
    check_digit = digits.pop()
    total = sum(digit * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(digits)))
    if (10 - total % 10) % 10 != check_digit:
        raise ValueError("barcode possui dígito verificador inválido.")
    return value


def validate_comment(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip()
    if len(normalized) > 1000:
        raise ValueError("comment deve ter no máximo 1.000 caracteres.")
    return normalized or None


def validate_review_reasons(
    reasons: list[tuple[str, str]],
    comment: str | None,
    *,
    require_other_comment: bool = True,
) -> None:
    """Valida motivos e a regra especial do aspecto ``other``."""

    if not reasons:
        raise ValueError("reasons deve conter pelo menos um motivo.")
    seen: set[str] = set()
    for aspect, perception in reasons:
        if aspect not in _REVIEW_ASPECTS:
            raise ValueError("aspect inválido.")
        if perception not in {"positive", "negative"}:
            raise ValueError("perception deve ser positive ou negative.")
        if aspect in seen:
            raise ValueError("Cada aspect pode aparecer apenas uma vez.")
        seen.add(aspect)
    if require_other_comment and "other" in seen and not validate_comment(comment):
        raise ValueError("comment é obrigatório quando aspect é other.")
