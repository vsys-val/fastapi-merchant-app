"""Consultas públicas, indicadores comunitários e listas pessoais."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.errors import ApiError
from app.models import Product, Review, User
from app.products import _public_product
from app.reviews import _public_review
from app.schemas import (
    CommunityReview,
    CommunityReviewPage,
    OwnProductPage,
    OwnReview,
    OwnReviewPage,
    ProductCommunitySummary,
    ProductDetail,
    ProductListCommunitySummary,
    ProductListItem,
    ProductPage,
)
from app.validation import identity_text, normalize_text, validate_gtin


def _validation_error(message: str) -> ApiError:
    return ApiError(422, "validation_error", message)


def _percentage(values: list[str], choices: tuple[str, ...]) -> dict[str, float]:
    total = len(values)
    counts = Counter(values)
    if total == 0:
        return {choice: 0.0 for choice in choices}
    return {choice: round(counts[choice] * 100 / total, 1) for choice in choices}


def _community_summary(reviews: list[Review]) -> ProductCommunitySummary:
    return ProductCommunitySummary(
        total_reviews=len(reviews),
        repurchase_intent=_percentage(
            [review.repurchase_intent for review in reviews],
            ("yes", "maybe", "no"),
        ),
        quality=_percentage(
            [review.quality for review in reviews],
            ("high", "adequate", "low"),
        ),
        expectation=_percentage(
            [review.expectation for review in reviews],
            ("exceeded", "met", "not_met"),
        ),
        value_for_money=_percentage(
            [review.value_for_money for review in reviews],
            ("good", "fair", "poor"),
        ),
    )


def _list_summary(reviews: list[Review]) -> ProductListCommunitySummary:
    return ProductListCommunitySummary(
        total_reviews=len(reviews),
        repurchase_intent=_percentage(
            [review.repurchase_intent for review in reviews],
            ("yes", "maybe", "no"),
        ),
    )


def _split_reviews(
    reviews: list[Review], current_user: User | None
) -> tuple[list[Review], Review | None]:
    if current_user is None:
        return reviews, None
    own = next((review for review in reviews if review.author_id == current_user.id), None)
    community = [review for review in reviews if review.author_id != current_user.id]
    return community, own


def search_products(
    session: Session,
    *,
    current_user: User | None,
    name: str | None,
    brand: str | None,
    category: str | None,
    barcode: str | None,
    page: int,
    page_size: int,
) -> ProductPage:
    if barcode is not None and any(value is not None for value in (name, brand, category)):
        raise _validation_error("barcode não pode ser combinado com outros filtros.")
    try:
        normalized_name = (
            identity_text(normalize_text(name, field="name", maximum=120))
            if name is not None
            else None
        )
        normalized_brand = (
            identity_text(normalize_text(brand, field="brand", maximum=80))
            if brand is not None
            else None
        )
        normalized_barcode = validate_gtin(barcode)
    except ValueError as exc:
        raise _validation_error(str(exc)) from None
    if normalized_name is not None and len(normalized_name) < 2:
        raise _validation_error("name deve ter pelo menos 2 caracteres.")
    if normalized_brand is not None and len(normalized_brand) < 2:
        raise _validation_error("brand deve ter pelo menos 2 caracteres.")

    products = list(
        session.scalars(select(Product).where(Product.deleted_at.is_(None))).all()
    )
    if normalized_barcode is not None:
        products = [product for product in products if product.barcode == normalized_barcode]
    else:
        if normalized_name is not None:
            products = [
                product
                for product in products
                if normalized_name in identity_text(product.name)
            ]
        if normalized_brand is not None:
            products = [
                product
                for product in products
                if normalized_brand in identity_text(product.brand)
            ]
        if category is not None:
            products = [product for product in products if product.category == category]
    products.sort(key=lambda product: (identity_text(product.name), identity_text(product.brand), product.id))
    total = len(products)
    start = (page - 1) * page_size
    selected = products[start : start + page_size]

    ids = [product.id for product in selected]
    reviews = (
        list(session.scalars(select(Review).where(Review.product_id.in_(ids))).all())
        if ids
        else []
    )
    by_product: dict[int, list[Review]] = {product_id: [] for product_id in ids}
    for review in reviews:
        by_product[review.product_id].append(review)

    items = []
    for product in selected:
        community, own = _split_reviews(by_product[product.id], current_user)
        items.append(
            ProductListItem(
                **_public_product(product).model_dump(),
                community_summary=_list_summary(community),
                your_repurchase_intent=own.repurchase_intent if own else None,
            )
        )
    return ProductPage(items=items, page=page, page_size=page_size, total=total)


def get_product_detail(
    session: Session, product_id: int, current_user: User | None
) -> ProductDetail:
    product = session.scalar(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    if product is None:
        raise ApiError(404, "product_not_found", "Produto não encontrado.")
    reviews = list(
        session.scalars(
            select(Review)
            .where(Review.product_id == product.id)
            .options(selectinload(Review.reasons))
        ).all()
    )
    community, own = _split_reviews(reviews, current_user)
    return ProductDetail(
        **_public_product(product).model_dump(),
        community_summary=_community_summary(community),
        your_review=_public_review(own) if own else None,
    )


def list_community_reviews(
    session: Session,
    product_id: int,
    current_user: User | None,
    page: int,
    page_size: int,
) -> CommunityReviewPage:
    product_exists = session.scalar(
        select(Product.id).where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    if product_exists is None:
        raise ApiError(404, "product_not_found", "Produto não encontrado.")
    filters = [Review.product_id == product_id]
    if current_user is not None:
        filters.append(Review.author_id != current_user.id)
    total = session.scalar(select(func.count()).select_from(Review).where(*filters)) or 0
    reviews = list(
        session.scalars(
            select(Review)
            .where(*filters)
            .options(selectinload(Review.reasons), joinedload(Review.author))
            .order_by(Review.created_at.desc(), Review.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    items = [
        CommunityReview(
            **_public_review(review).model_dump(),
            author_name=review.author.public_name,
        )
        for review in reviews
    ]
    return CommunityReviewPage(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


def list_own_reviews(
    session: Session, current_user: User, page: int, page_size: int
) -> OwnReviewPage:
    filters = [Review.author_id == current_user.id]
    total = session.scalar(select(func.count()).select_from(Review).where(*filters)) or 0
    reviews = list(
        session.scalars(
            select(Review)
            .where(*filters)
            .options(selectinload(Review.reasons), joinedload(Review.product))
            .order_by(Review.created_at.desc(), Review.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return OwnReviewPage(
        items=[
            OwnReview(
                **_public_review(review).model_dump(),
                product=_public_product(review.product),
            )
            for review in reviews
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


def list_own_products(
    session: Session, current_user: User, page: int, page_size: int
) -> OwnProductPage:
    filters = [
        Product.responsible_id == current_user.id,
        Product.deleted_at.is_(None),
    ]
    total = session.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    products = list(
        session.scalars(
            select(Product)
            .where(*filters)
            .order_by(Product.created_at.desc(), Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return OwnProductPage(
        items=[_public_product(product) for product in products],
        page=page,
        page_size=page_size,
        total=total,
    )
