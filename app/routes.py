"""Rotas funcionais implementadas na entrega de autenticação."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import create_user, current_user_response, get_current_user, login
from app.database import get_db
from app.models import User
from app.products import create_product, delete_product, update_product
from app.schemas import (
    LoginInput,
    ProductCreate,
    ProductPatch,
    ProductPublic,
    TokenResponse,
    UserCreate,
    UserPublic,
)


router = APIRouter(prefix="/api/v1")


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, session: Session = Depends(get_db)) -> UserPublic:
    return create_user(payload, session)


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
