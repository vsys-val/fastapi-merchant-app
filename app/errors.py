"""Envelope público e seguro para erros da API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    details: Any = None
    headers: dict[str, str] | None = None


def _field_path(location: tuple[Any, ...]) -> str:
    path = ""
    for part in location:
        if part in {"body", "query", "path", "header", "cookie"}:
            continue
        if isinstance(part, int):
            path += f"[{part}]"
        elif path:
            path += f".{part}"
        else:
            path = str(part)
    return path or "request"


def _validation_code(error_type: str) -> str:
    if error_type == "missing":
        return "required"
    if error_type in {"literal_error", "enum"}:
        return "invalid_choice"
    if error_type.endswith("_too_short"):
        return "too_short"
    if error_type.endswith("_too_long"):
        return "too_long"
    return "invalid"


def _validation_message(error_type: str) -> str:
    messages = {
        "missing": "Campo obrigatório.",
        "literal_error": "Valor não permitido.",
        "enum": "Valor não permitido.",
        "string_too_short": "Texto menor que o permitido.",
        "string_too_long": "Texto maior que o permitido.",
        "too_short": "Quantidade de itens menor que a permitida.",
        "too_long": "Quantidade de itens maior que a permitida.",
    }
    return messages.get(error_type, "Valor inválido.")


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": _field_path(tuple(error["loc"])),
                "code": _validation_code(str(error["type"])),
                "message": _validation_message(str(error["type"])),
            }
            for error in exception.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Os dados enviados são inválidos.",
                    "details": details,
                }
            },
        )

    @application.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exception: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exception.status_code,
            headers=exception.headers,
            content={
                "error": {
                    "code": exception.code,
                    "message": exception.message,
                    "details": exception.details,
                }
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request, exception: StarletteHTTPException
    ) -> JSONResponse:
        code = "not_found" if exception.status_code == 404 else "http_error"
        message = (
            "Recurso não encontrado."
            if exception.status_code == 404
            else "A requisição não pôde ser concluída."
        )
        return JSONResponse(
            status_code=exception.status_code,
            content={"error": {"code": code, "message": message, "details": None}},
        )
