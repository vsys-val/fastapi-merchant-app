"""Casos de uso transacionais para avaliações e seus motivos."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Product, Review, ReviewReason, User
from app.schemas import ReviewCreate, ReviewPatch, ReviewPublic, ReviewReasonPublic
from app.validation import validate_review_reasons


_REVIEW_UNIQUE_CONSTRAINT = "uq_avaliacoes_usuario_produto"


def _public_review(review: Review) -> ReviewPublic:
    reasons = sorted(review.reasons, key=lambda reason: reason.id or 0)
    return ReviewPublic(
        id=review.id,
        repurchase_intent=review.repurchase_intent,
        quality=review.quality,
        expectation=review.expectation,
        value_for_money=review.value_for_money,
        reasons=[
            ReviewReasonPublic(aspect=reason.aspect, perception=reason.perception)
            for reason in reasons
        ],
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _review_conflict(existing_review_id: int | None = None) -> ApiError:
    return ApiError(
        409,
        "review_already_exists",
        "Você já avaliou este produto.",
        {"existing_review_id": existing_review_id} if existing_review_id is not None else None,
    )


def _is_review_uniqueness_error(exception: IntegrityError) -> bool:
    original = exception.orig
    diagnostic = getattr(original, "diag", None)
    return (
        getattr(original, "sqlstate", None) == "23505"
        and getattr(diagnostic, "constraint_name", None) == _REVIEW_UNIQUE_CONSTRAINT
    )


def _reason_models(payload: ReviewCreate | ReviewPatch) -> list[ReviewReason]:
    assert payload.reasons is not None
    return [
        ReviewReason(aspect=reason.aspect, perception=reason.perception)
        for reason in payload.reasons
    ]


def _validate_final_reasons(
    reasons: list[tuple[str, str]], comment: str | None
) -> None:
    try:
        validate_review_reasons(reasons, comment)
    except ValueError:
        raise ApiError(
            422,
            "validation_error",
            "A avaliação resultante é inválida.",
        ) from None


def create_review(
    product_id: int,
    payload: ReviewCreate,
    current_user: User,
    session: Session,
) -> ReviewPublic:
    product = session.scalar(
        select(Product)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
        .with_for_update(read=True, key_share=True)
    )
    if product is None:
        raise ApiError(404, "product_not_found", "Produto não encontrado.")

    existing = session.scalar(
        select(Review.id).where(
            Review.product_id == product.id,
            Review.author_id == current_user.id,
        )
    )
    if existing is not None:
        raise _review_conflict(existing)

    review = Review(
        author_id=current_user.id,
        product_id=product.id,
        repurchase_intent=payload.repurchase_intent,
        quality=payload.quality,
        expectation=payload.expectation,
        value_for_money=payload.value_for_money,
        comment=payload.comment,
        reasons=_reason_models(payload),
    )
    session.add(review)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if not _is_review_uniqueness_error(exc):
            raise
        existing = session.scalar(
            select(Review.id).where(
                Review.product_id == product_id,
                Review.author_id == current_user.id,
            )
        )
        raise _review_conflict(existing) from exc
    session.refresh(review)
    return _public_review(review)


def update_review(
    review_id: int,
    payload: ReviewPatch,
    current_user: User,
    session: Session,
) -> ReviewPublic:
    review = session.scalar(select(Review).where(Review.id == review_id).with_for_update())
    if review is None:
        raise ApiError(404, "review_not_found", "Avaliação não encontrada.")
    if review.author_id != current_user.id:
        raise ApiError(403, "review_forbidden", "Você não pode editar esta avaliação.")

    values = payload.model_dump(exclude_unset=True, exclude={"reasons"})
    repurchase_intent = values.get("repurchase_intent", review.repurchase_intent)
    quality = values.get("quality", review.quality)
    expectation = values.get("expectation", review.expectation)
    value_for_money = values.get("value_for_money", review.value_for_money)
    comment = values.get("comment", review.comment)
    if "reasons" in payload.model_fields_set:
        assert payload.reasons is not None
        reason_values = [
            (reason.aspect, reason.perception) for reason in payload.reasons
        ]
    else:
        reason_values = [(reason.aspect, reason.perception) for reason in review.reasons]
    _validate_final_reasons(reason_values, comment)

    review.repurchase_intent = repurchase_intent
    review.quality = quality
    review.expectation = expectation
    review.value_for_money = value_for_money
    review.comment = comment
    try:
        if "reasons" in payload.model_fields_set:
            review.reasons.clear()
            session.flush()
            review.reasons.extend(_reason_models(payload))
        review.updated_at = datetime.now(timezone.utc)
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(review)
    return _public_review(review)


def delete_review(review_id: int, current_user: User, session: Session) -> None:
    review = session.scalar(select(Review).where(Review.id == review_id).with_for_update())
    if review is None:
        raise ApiError(404, "review_not_found", "Avaliação não encontrada.")
    if review.author_id != current_user.id:
        raise ApiError(403, "review_forbidden", "Você não pode excluir esta avaliação.")
    session.delete(review)
    session.commit()
