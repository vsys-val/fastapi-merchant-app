"""Rotas funcionais implementadas na entrega de autenticação."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.auth import create_user, current_user_response, login
from app.database import get_db
from app.schemas import LoginInput, TokenResponse, UserCreate, UserPublic


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
