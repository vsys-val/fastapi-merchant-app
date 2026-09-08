"""Schemas públicos de entrada, separados das entidades SQLAlchemy."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.security import validate_password_policy

from app.validation import (
    normalize_quantity,
    normalize_text,
    normalize_unit,
    normalize_variant,
    parse_quantity,
    validate_comment,
    validate_gtin,
    validate_review_reasons,
)

Category = Literal[
    "food",
    "beverages",
    "cleaning",
    "personal_hygiene",
    "household_utilities",
    "other",
]
Aspect = Literal[
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
]
Perception = Literal["positive", "negative"]
RepurchaseIntent = Literal["yes", "maybe", "no"]
Quality = Literal["low", "adequate", "high"]
Expectation = Literal["not_met", "met", "exceeded"]
ValueForMoney = Literal["poor", "fair", "good"]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserCreate(StrictInput):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=15, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().casefold() if isinstance(value, str) else value

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return normalize_text(value, field="name", maximum=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_policy(value)


class UserPublic(BaseModel):
    id: int
    name: str
    email: EmailStr


class LoginInput(StrictInput):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().casefold() if isinstance(value, str) else value


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: Literal[86400] = 86400


class ProductCreate(StrictInput):
    name: str = Field(min_length=2, max_length=120)
    brand: str = Field(min_length=1, max_length=80)
    variant: str | None = Field(default=None, max_length=80)
    quantity: Decimal
    unit: str
    category: Category
    barcode: str | None = None

    @field_validator("name", "brand", mode="before")
    @classmethod
    def clean_required_text(cls, value: str, info):
        return normalize_text(value, field=info.field_name, maximum=120 if info.field_name == "name" else 80)

    @field_validator("variant", mode="before")
    @classmethod
    def clean_variant(cls, value: str | None):
        value = normalize_variant(value)
        if value is not None and len(value) > 80:
            raise ValueError("variant deve ter no máximo 80 caracteres.")
        return value

    @field_validator("quantity", mode="before")
    @classmethod
    def parse_quantity_value(cls, value):
        return parse_quantity(value)

    @field_validator("unit", mode="before")
    @classmethod
    def clean_unit(cls, value):
        return normalize_unit(value)

    @field_validator("barcode", mode="before")
    @classmethod
    def check_barcode(cls, value):
        return validate_gtin(value)

    @model_validator(mode="after")
    def canonicalize_quantity(self):
        normalized = normalize_quantity(self.quantity, self.unit)
        self.quantity = normalized.value
        self.unit = normalized.unit
        return self


class ProductPublic(BaseModel):
    id: int
    name: str
    brand: str
    variant: str | None
    quantity: Decimal
    unit: Literal["g", "ml", "un"]
    category: Category
    barcode: str | None

    @field_serializer("quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> int | float:
        if value == value.to_integral_value():
            return int(value)
        return float(value)


class ProductPatch(StrictInput):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    brand: str | None = Field(default=None, max_length=80)
    variant: str | None = Field(default=None, max_length=80)
    quantity: Decimal | None = None
    unit: str | None = None
    category: Category | None = None
    barcode: str | None = None

    @field_validator("name", "brand", mode="before")
    @classmethod
    def clean_patch_text(cls, value: str | None, info):
        if value is None:
            return value
        return normalize_text(value, field=info.field_name, maximum=120 if info.field_name == "name" else 80)

    @field_validator("variant", mode="before")
    @classmethod
    def clean_patch_variant(cls, value: str | None):
        value = normalize_variant(value)
        if value is not None and len(value) > 80:
            raise ValueError("variant deve ter no máximo 80 caracteres.")
        return value

    @field_validator("quantity", mode="before")
    @classmethod
    def parse_patch_quantity(cls, value):
        return None if value is None else parse_quantity(value)

    @field_validator("unit", mode="before")
    @classmethod
    def clean_patch_unit(cls, value):
        return None if value is None else normalize_unit(value)

    @field_validator("barcode", mode="before")
    @classmethod
    def check_patch_barcode(cls, value):
        return validate_gtin(value)

    @model_validator(mode="after")
    def validate_patch_semantics(self):
        if not self.model_fields_set:
            raise ValueError("Envie pelo menos um campo para alterar.")
        for field_name in ("name", "brand", "category"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} é obrigatório e não pode ser null.")
        quantity_sent = "quantity" in self.model_fields_set
        unit_sent = "unit" in self.model_fields_set
        if quantity_sent and self.quantity is None:
            raise ValueError("quantity é obrigatório e não pode ser null.")
        if unit_sent and self.unit is None:
            raise ValueError("unit é obrigatório e não pode ser null.")
        if quantity_sent and unit_sent:
            normalized = normalize_quantity(self.quantity, self.unit)
            self.quantity = normalized.value
            self.unit = normalized.unit
        return self


class ReviewReasonInput(StrictInput):
    aspect: Aspect
    perception: Perception


class ReviewReasonPublic(BaseModel):
    aspect: Aspect
    perception: Perception


class ReviewCreate(StrictInput):
    repurchase_intent: RepurchaseIntent
    quality: Quality
    expectation: Expectation
    value_for_money: ValueForMoney
    reasons: list[ReviewReasonInput] = Field(min_length=1, max_length=12)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment", mode="before")
    @classmethod
    def clean_review_comment(cls, value):
        return validate_comment(value)

    @model_validator(mode="after")
    def validate_review(self):
        validate_review_reasons(
            [(reason.aspect, reason.perception) for reason in self.reasons], self.comment
        )
        return self


class ReviewPatch(StrictInput):
    repurchase_intent: RepurchaseIntent | None = None
    quality: Quality | None = None
    expectation: Expectation | None = None
    value_for_money: ValueForMoney | None = None
    reasons: list[ReviewReasonInput] | None = Field(default=None, max_length=12)
    comment: str | None = None

    @field_validator("comment", mode="before")
    @classmethod
    def clean_patch_comment(cls, value):
        return validate_comment(value)

    @model_validator(mode="after")
    def validate_patch_review(self):
        if not self.model_fields_set:
            raise ValueError("Envie pelo menos um campo para alterar.")
        for field_name in (
            "repurchase_intent",
            "quality",
            "expectation",
            "value_for_money",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} é obrigatório e não pode ser null.")
        if "reasons" in self.model_fields_set:
            if self.reasons is None:
                raise ValueError("reasons não pode ser null.")
            validate_review_reasons(
                [(reason.aspect, reason.perception) for reason in self.reasons],
                self.comment,
                require_other_comment="comment" in self.model_fields_set,
            )
        return self


class ReviewPublic(BaseModel):
    id: int
    repurchase_intent: RepurchaseIntent
    quality: Quality
    expectation: Expectation
    value_for_money: ValueForMoney
    reasons: list[ReviewReasonPublic]
    comment: str | None
    created_at: datetime
    updated_at: datetime
