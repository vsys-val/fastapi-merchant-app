"""Casos de uso transacionais para criação, edição e exclusão de produtos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Product, Review, User
from app.schemas import ProductCreate, ProductPatch, ProductPublic
from app.validation import build_identity_key, normalize_quantity


_PRODUCT_UNIQUE_CONSTRAINTS = {
    "produtos_codigo_barras_key",
    "produtos_chave_identidade_key",
}


@dataclass(frozen=True, slots=True)
class ProductMutationResult:
    product: ProductPublic
    created: bool


def _public_product(product: Product) -> ProductPublic:
    return ProductPublic(
        id=product.id,
        name=product.name,
        brand=product.brand,
        variant=product.variant,
        quantity=product.quantity,
        unit=product.unit,
        category=product.category,
        barcode=product.barcode,
    )


def _identity_for(payload: ProductCreate) -> str:
    return build_identity_key(
        name=payload.name,
        brand=payload.brand,
        variant=payload.variant,
        quantity=payload.quantity,
        unit=payload.unit,
    )


def _matching_products(
    session: Session,
    *,
    identity_key: str,
    barcode: str | None,
    exclude_id: int | None = None,
    lock: bool = False,
) -> list[Product]:
    predicates = [Product.identity_key == identity_key]
    if barcode is not None:
        predicates.append(Product.barcode == barcode)
    statement = select(Product).where(or_(*predicates)).order_by(Product.id)
    if exclude_id is not None:
        statement = statement.where(Product.id != exclude_id)
    if lock:
        statement = statement.with_for_update()
    return list(session.scalars(statement).all())


def _product_conflict(products: list[Product]) -> ApiError:
    identifiers = sorted({product.id for product in products})
    details: dict[str, int] | None
    if len(identifiers) == 1:
        details = {"existing_product_id": identifiers[0]}
    else:
        details = None
    return ApiError(
        409,
        "product_conflict",
        "Este produto já está cadastrado.",
        details,
    )


def _has_any_review(session: Session, product_id: int) -> bool:
    return session.scalar(select(Review.id).where(Review.product_id == product_id).limit(1)) is not None


def _find_conflict_after_integrity_error(
    session: Session,
    *,
    identity_key: str,
    barcode: str | None,
    fallback_id: int | None = None,
) -> ApiError:
    matches = _matching_products(
        session,
        identity_key=identity_key,
        barcode=barcode,
        exclude_id=fallback_id,
    )
    if matches:
        return _product_conflict(matches)
    return ApiError(409, "product_conflict", "Este produto já está cadastrado.")


def _is_product_uniqueness_error(exception: IntegrityError) -> bool:
    original = exception.orig
    sqlstate = getattr(original, "sqlstate", None)
    diagnostic = getattr(original, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    return sqlstate == "23505" and constraint_name in _PRODUCT_UNIQUE_CONSTRAINTS


def create_product(
    payload: ProductCreate,
    current_user: User,
    session: Session,
) -> ProductMutationResult:
    identity_key = _identity_for(payload)
    matches = _matching_products(
        session,
        identity_key=identity_key,
        barcode=payload.barcode,
        lock=True,
    )

    if len(matches) > 1:
        raise _product_conflict(matches)
    if matches and matches[0].deleted_at is None:
        raise _product_conflict(matches)

    if matches:
        product = matches[0]
        if _has_any_review(session, product.id):
            raise _product_conflict(matches)
        product.responsible_id = current_user.id
        product.name = payload.name
        product.brand = payload.brand
        product.variant = payload.variant
        product.quantity = payload.quantity
        product.unit = payload.unit
        product.category = payload.category
        product.barcode = payload.barcode
        product.identity_key = identity_key
        product.deleted_at = None
        product.updated_at = datetime.now(timezone.utc)
        created = False
    else:
        product = Product(
            responsible_id=current_user.id,
            name=payload.name,
            brand=payload.brand,
            variant=payload.variant,
            quantity=payload.quantity,
            unit=payload.unit,
            category=payload.category,
            barcode=payload.barcode,
            identity_key=identity_key,
        )
        session.add(product)
        created = True

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if not _is_product_uniqueness_error(exc):
            raise
        raise _find_conflict_after_integrity_error(
            session,
            identity_key=identity_key,
            barcode=payload.barcode,
        ) from exc
    session.refresh(product)
    return ProductMutationResult(_public_product(product), created=created)


def update_product(
    product_id: int,
    payload: ProductPatch,
    current_user: User,
    session: Session,
) -> ProductPublic:
    product = session.scalar(
        select(Product)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
        .with_for_update()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "Produto não encontrado.")
    if product.responsible_id != current_user.id:
        raise ApiError(403, "product_forbidden", "Você não pode editar este produto.")

    another_author_review = session.scalar(
        select(Review.id)
        .where(Review.product_id == product.id, Review.author_id != current_user.id)
        .limit(1)
    )
    if another_author_review is not None:
        raise ApiError(
            409,
            "product_locked_by_reviews",
            "O produto não pode ser editado porque outra pessoa já o avaliou.",
        )

    values = payload.model_dump(exclude_unset=True)
    name = values.get("name", product.name)
    brand = values.get("brand", product.brand)
    variant = values.get("variant", product.variant)
    category = values.get("category", product.category)
    barcode = values.get("barcode", product.barcode)
    source_quantity = values.get("quantity", product.quantity)
    source_unit = values.get("unit", product.unit)
    normalized = normalize_quantity(source_quantity, source_unit)
    identity_key = build_identity_key(
        name=name,
        brand=brand,
        variant=variant,
        quantity=normalized.value,
        unit=normalized.unit,
    )

    conflicts = _matching_products(
        session,
        identity_key=identity_key,
        barcode=barcode,
        exclude_id=product.id,
        lock=False,
    )
    if conflicts:
        raise _product_conflict(conflicts)

    product.name = name
    product.brand = brand
    product.variant = variant
    product.quantity = normalized.value
    product.unit = normalized.unit
    product.category = category
    product.barcode = barcode
    product.identity_key = identity_key
    product.updated_at = datetime.now(timezone.utc)
    current_product_id = product.id
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if not _is_product_uniqueness_error(exc):
            raise
        raise _find_conflict_after_integrity_error(
            session,
            identity_key=identity_key,
            barcode=barcode,
            fallback_id=current_product_id,
        ) from exc
    session.refresh(product)
    return _public_product(product)


def delete_product(product_id: int, current_user: User, session: Session) -> None:
    product = session.scalar(
        select(Product)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
        .with_for_update()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "Produto não encontrado.")
    if product.responsible_id != current_user.id:
        raise ApiError(403, "product_forbidden", "Você não pode excluir este produto.")
    if _has_any_review(session, product.id):
        raise ApiError(
            409,
            "product_has_reviews",
            "O produto não pode ser excluído enquanto possuir avaliações.",
        )
    product.deleted_at = datetime.now(timezone.utc)
    product.updated_at = product.deleted_at
    session.commit()
