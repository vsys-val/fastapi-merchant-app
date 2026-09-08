"""Verificação operacional da aplicação e da conexão PostgreSQL."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.schemas import ErrorResponse, HealthResponse


router = APIRouter(tags=["Operational"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Falha interna inesperada."},
        503: {"model": ErrorResponse, "description": "Banco de dados indisponível."},
    },
    summary="Verificar saúde da aplicação",
    description="Confirma que a API responde e que o PostgreSQL aceita consultas.",
)
def health_check(session: Session = Depends(get_db)) -> HealthResponse:
    try:
        session.execute(select(1)).scalar_one()
    except SQLAlchemyError:
        raise ApiError(
            503,
            "database_unavailable",
            "O banco de dados está temporariamente indisponível.",
        ) from None
    return HealthResponse()
