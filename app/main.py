"""Ponto de entrada: uvicorn app.main:create_app --factory --reload."""

from fastapi import FastAPI

from app.config import load_settings


def create_app() -> FastAPI:
    settings = load_settings()
    application = FastAPI(
        title="FastAPI Merchant App",
        version="0.1.0",
        description="Catálogo compartilhado e avaliações de produtos. Em implementação.",
        debug=False,
    )
    application.state.settings = settings
    return application
