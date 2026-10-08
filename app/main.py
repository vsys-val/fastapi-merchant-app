"""Ponto de entrada: uvicorn app.main:create_app --factory --reload."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import load_settings
from app.database import get_session_factory
from app.email import build_email_sender
from app.observability import RequestMetrics, install_request_metrics
from app.errors import register_exception_handlers
from app.health import router as health_router
from app.routes import router


class ApiNoStoreMiddleware:
    """Protect API responses, including errors emitted outside user middleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path == "/api" or path.startswith("/api/")):
            await self.app(scope, receive, send)
            return

        async def send_no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                # A public catalog response may also contain the viewer's own rating.
                # No API response is safe for storage by a browser or shared cache.
                MutableHeaders(scope=message)["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_no_store)


class MerchantAPI(FastAPI):
    def build_middleware_stack(self) -> ASGIApp:
        # Wrap ServerErrorMiddleware too, so unexpected 500s obey the same policy.
        return ApiNoStoreMiddleware(super().build_middleware_stack())


def create_app() -> FastAPI:
    settings = load_settings()
    application = MerchantAPI(
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
    application.state.email_sender = build_email_sender(settings)
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Merchant-Client"],
        )
    install_request_metrics(application, RequestMetrics(), lambda: get_session_factory()())
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
