"""Rotas HTTP funcionais do MVP."""

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import (
    confirm_password_reset,
    create_user,
    current_user_response,
    get_current_user,
    get_optional_user,
    login,
    request_password_reset,
    resend_verification,
    verify_email,
)
from app.catalog import (
    get_product_detail,
    list_community_reviews,
    list_own_products,
    list_own_reviews,
    search_products,
)
from app.database import get_db
from app.email import EmailMessage, deliver
from app.errors import ApiError
from app.models import User
from app.products import create_product, delete_product, update_product
from app.reviews import create_review, delete_review, update_review
from app.schemas import (
    EmailInput,
    EmailVerificationInput,
    LoginInput,
    PasswordResetConfirm,
    Category,
    CommunityReviewPage,
    ErrorResponse,
    OwnProductPage,
    OwnReviewPage,
    ProductCreate,
    ProductDetail,
    ProductPage,
    ProductPatch,
    ProductPublic,
    ReviewCreate,
    ReviewPatch,
    ReviewPublic,
    TokenResponse,
    UserCreate,
    UserPublic,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["API"],
    responses={
        500: {"model": ErrorResponse, "description": "Falha interna inesperada."},
    },
)


def _send_later(
    request: Request, background_tasks: BackgroundTasks, message: EmailMessage | None
) -> None:
    """Envia depois da resposta: o tempo de resposta não revela contas."""

    sender = request.app.state.email_sender
    if message is not None and sender is not None:
        background_tasks.add_task(deliver, sender, message)


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> UserPublic:
    result = create_user(payload, request, session)
    _send_later(request, background_tasks, result.email)
    return result.user


@router.post("/auth/email-verification", response_model=TokenResponse)
def confirm_email(
    payload: EmailVerificationInput,
    request: Request,
    session: Session = Depends(get_db),
) -> TokenResponse:
    return verify_email(payload, request, session)


@router.post("/auth/email-verification/resend", status_code=status.HTTP_202_ACCEPTED)
def resend_email_verification(
    payload: EmailInput,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> Response:
    _send_later(request, background_tasks, resend_verification(payload, request, session))
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/auth/password-reset", status_code=status.HTTP_202_ACCEPTED)
def start_password_reset(
    payload: EmailInput,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> Response:
    _send_later(request, background_tasks, request_password_reset(payload, request, session))
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/auth/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def finish_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    session: Session = Depends(get_db),
) -> Response:
    confirm_password_reset(payload, request, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/auth/login", response_model=TokenResponse)
def authenticate(
    payload: LoginInput,
    request: Request,
    session: Session = Depends(get_db),
) -> TokenResponse:
    return login(payload, request, session)


@router.get("/users/me", response_model=UserPublic)
def read_current_user(user: UserPublic = Depends(current_user_response)) -> UserPublic:
    return user


@router.get("/users/me/reviews", response_model=OwnReviewPage)
def read_own_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> OwnReviewPage:
    return list_own_reviews(session, current_user, page, page_size)


@router.get("/users/me/products", response_model=OwnProductPage)
def read_own_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> OwnProductPage:
    return list_own_products(session, current_user, page, page_size)


@router.get("/products", response_model=ProductPage)
def read_products(
    request: Request,
    name: str | None = Query(default=None, min_length=2, max_length=120),
    brand: str | None = Query(default=None, min_length=2, max_length=80),
    category: Category | None = Query(default=None),
    barcode: str | None = Query(default=None, max_length=14),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    session: Session = Depends(get_db),
) -> ProductPage:
    if len(request.query_params.getlist("category")) > 1:
        raise ApiError(422, "validation_error", "category não pode ser repetida.")
    return search_products(
        session,
        current_user=current_user,
        name=name,
        brand=brand,
        category=category,
        barcode=barcode,
        page=page,
        page_size=page_size,
    )


@router.get("/products/{product_id}", response_model=ProductDetail)
def read_product(
    product_id: int,
    current_user: User | None = Depends(get_optional_user),
    session: Session = Depends(get_db),
) -> ProductDetail:
    return get_product_detail(session, product_id, current_user)


@router.get("/products/{product_id}/reviews", response_model=CommunityReviewPage)
def read_product_reviews(
    product_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    session: Session = Depends(get_db),
) -> CommunityReviewPage:
    return list_community_reviews(session, product_id, current_user, page, page_size)


@router.post("/products", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def register_product(
    payload: ProductCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ProductPublic:
    result = create_product(payload, current_user, session)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return result.product


@router.patch("/products/{product_id}", response_model=ProductPublic)
def edit_product(
    product_id: int,
    payload: ProductPatch,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ProductPublic:
    return update_product(product_id, payload, current_user, session)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    delete_product(product_id, current_user, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/products/{product_id}/reviews",
    response_model=ReviewPublic,
    status_code=status.HTTP_201_CREATED,
)
def register_review(
    product_id: int,
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ReviewPublic:
    return create_review(product_id, payload, current_user, session)


@router.patch("/reviews/{review_id}", response_model=ReviewPublic)
def edit_review(
    review_id: int,
    payload: ReviewPatch,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ReviewPublic:
    return update_review(review_id, payload, current_user, session)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    delete_review(review_id, current_user, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
