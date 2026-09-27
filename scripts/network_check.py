"""Mede como o IP do cliente chega à API, direto e pelo proxy do site.

Roda no GitHub Actions (workflow network-check). Descobre o IP público do
runner e mostra em que posição ele aparece em cada caminho, para escolher
a regra de IP dos limites por IP.
"""

from __future__ import annotations

import json
from urllib.request import Request, urlopen

PATHS = {
    "direto (API)": "https://fastapi-merchant-app.onrender.com/api/v1/network-check",
    "pelo site (proxy)": "https://merchant-app-web.onrender.com/api/v1/network-check",
}


def get(url: str) -> tuple[int, str]:
    with urlopen(Request(url, headers={"User-Agent": "merchant-network-check"}), timeout=90) as response:
        return response.status, response.read().decode()


def main() -> None:
    _, runner_ip = get("https://api.ipify.org")
    print(f"IP público do runner: {runner_ip}\n")
    for label, url in PATHS.items():
        try:
            status, body = get(url)
        except Exception as exc:  # noqa: BLE001 - diagnóstico: registrar e seguir
            print(f"== {label}: falhou ({exc})\n")
            continue
        print(f"== {label}: HTTP {status}")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            print(f"resposta não JSON (primeiros 200 caracteres): {body[:200]!r}\n")
            continue
        print(json.dumps(data, indent=2))
        chain = data.get("forwarded_for", [])
        position = chain.index(runner_ip) if runner_ip in chain else None
        print(f"posição do IP do runner no X-Forwarded-For: {position} de {len(chain)}")
        print(f"client_host é o runner? {data.get('client_host') == runner_ip}\n")


if __name__ == "__main__":
    main()
