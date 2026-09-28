"""Sessão do navegador em cookie HttpOnly (ADR-0016).

O frontend chama a API pela própria origem (proxy /api/* do site), então o
cookie é "de primeira parte": o JavaScript não o lê, o que tira o token do
alcance de um XSS. O cabeçalho Authorization continua valendo para clientes
que não são o navegador (Swagger, scripts, smoke test).
"""

from __future__ import annotations

from fastapi import Request, Response

from app.errors import ApiError

COOKIE_NAME = "merchant_session"
COOKIE_PATH = "/api"
# Toda escrita autenticada por cookie precisa deste cabeçalho. Um site de
# terceiros não consegue enviá-lo sem passar pelo CORS, que só libera o site.
CSRF_HEADER = "X-Merchant-Client"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def set_session_cookie(request: Request, response: Response, token: str) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.access_token_expires_seconds,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
    )


def clear_session_cookie(request: Request, response: Response) -> None:
    settings = request.app.state.settings
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
    )


def session_cookie_token(request: Request) -> str | None:
    """Token do cookie, exigindo o cabeçalho anti-CSRF nas escritas."""

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    if request.method not in SAFE_METHODS and not request.headers.get(CSRF_HEADER):
        raise ApiError(403, "csrf_header_required", "Requisição recusada: cabeçalho de segurança ausente.")
    return token
