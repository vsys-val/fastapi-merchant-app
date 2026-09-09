"""Ponto de entrada: uvicorn app.main:create_app --factory --reload."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_settings
from app.errors import register_exception_handlers
from app.health import router as health_router
from app.routes import router


def create_app() -> FastAPI:
    settings = load_settings()
    application = FastAPI(
        title="FastAPI Merchant App",
        version="1.0.0",
        description=(
            "API do MVP para catálogo compartilhado de produtos e avaliações "
            "com indicadores comunitários."
        ),
        openapi_tags=[
            {"name": "API", "description": "Operações do catálogo, contas e avaliações."},
            {"name": "Operational", "description": "Disponibilidade da aplicação."},
        ],
        debug=False,
    )
    application.state.settings = settings
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    register_exception_handlers(application)
    application.include_router(router)
    application.include_router(health_router)

    schema = application.openapi()
    for path in (
        "/api/v1/products",
        "/api/v1/products/{product_id}",
        "/api/v1/products/{product_id}/reviews",
    ):
        operation = schema.get("paths", {}).get(path, {}).get("get")
        if operation is not None:
            operation["security"] = [{"BearerAuth": []}, {}]
    application.openapi_schema = schema
    return application
