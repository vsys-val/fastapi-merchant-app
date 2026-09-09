"""Smoke test não destrutivo da API publicada."""

from __future__ import annotations

import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://fastapi-merchant-app.onrender.com"
EXPECTED_PATHS = {
    "/health",
    "/api/v1/users",
    "/api/v1/auth/login",
    "/api/v1/products",
    "/api/v1/products/{product_id}",
    "/api/v1/products/{product_id}/reviews",
    "/api/v1/reviews/{review_id}",
}


def request(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data else {}
    req = Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw) if raw else {}


def wait_until_awake() -> dict:
    last_error: Exception | None = None
    for _ in range(6):
        try:
            status, payload = request("/health")
            if status == 200:
                return payload
        except (TimeoutError, URLError) as exc:
            last_error = exc
        time.sleep(10)
    raise RuntimeError("A API não ficou disponível dentro do prazo.") from last_error


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> int:
    health = wait_until_awake()
    check(
        health == {"status": "healthy", "database": "available"},
        "API e banco estão disponíveis",
    )

    status, schema = request("/openapi.json")
    check(status == 200, "OpenAPI está público")
    check(EXPECTED_PATHS <= set(schema.get("paths", {})), "rotas essenciais estão publicadas")

    status, page = request("/api/v1/products?page=1&page_size=1")
    check(status == 200, "catálogo público responde")
    check(set(page) == {"items", "page", "page_size", "total"}, "paginação mantém o contrato")

    status, error = request(
        "/api/v1/products",
        method="POST",
        body={
            "name": "Não deve ser salvo",
            "brand": "Smoke test",
            "quantity": 1,
            "unit": "un",
            "category": "other",
        },
    )
    check(status == 401, "mutação sem token é rejeitada")
    check(
        error.get("error", {}).get("code") == "invalid_authentication",
        "erro mantém o envelope público",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
