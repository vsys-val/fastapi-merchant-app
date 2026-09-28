"""Endereço IP do cliente para os limites por IP (ADR-0016).

Na produção, toda requisição chega por uma cadeia de proxies que acrescentam
ao ``X-Forwarded-For`` o endereço de quem os chamou:

- direto: ``cliente, borda Cloudflare, balanceador do Render (10.x)``;
- pelo site: ``cliente, borda Cloudflare do site (x2), saída do site estático
  no Render, borda Cloudflare da API, balanceador``.

O primeiro item da lista é escrito por quem faz a requisição e pode ser
forjado: basta enviar o próprio ``X-Forwarded-For``. Por isso a lista é lida da
direita para a esquerda, pulando só saltos conhecidos (endereços privados,
Cloudflare e a saída do site estático). O primeiro endereço que sobra é o
cliente. Se um salto desconhecido aparecer (por exemplo, o Render mudar a
saída do site), o limite passa a valer para esse salto: mais restritivo, nunca
contornável.
"""

from __future__ import annotations

from functools import lru_cache
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network

from fastapi import Request

# https://www.cloudflare.com/ips/ (estável; revisar se a medição mudar).
CLOUDFLARE_NETWORKS = (
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32",
)


@lru_cache(maxsize=8)
def _trusted_networks(extra: str) -> tuple[IPv4Network | IPv6Network, ...]:
    configured = [item.strip() for item in extra.split(",") if item.strip()]
    return tuple(ip_network(network) for network in (*CLOUDFLARE_NETWORKS, *configured))


def _is_trusted_hop(value: str, networks: tuple[IPv4Network | IPv6Network, ...]) -> bool | None:
    """``True`` para salto conhecido, ``False`` para cliente, ``None`` se inválido."""

    try:
        address = ip_address(value)
    except ValueError:
        return None
    if address.is_private or address.is_loopback or address.is_link_local:
        return True
    return any(address in network for network in networks)


def forwarded_chain(request: Request) -> list[str]:
    return [
        part.strip()
        for header in request.headers.getlist("x-forwarded-for")
        for part in header.split(",")
        if part.strip()
    ]


def client_ip(request: Request) -> str:
    networks = _trusted_networks(request.app.state.settings.trusted_proxy_networks)
    last_hop: str | None = None
    for value in reversed(forwarded_chain(request)):
        trusted = _is_trusted_hop(value, networks)
        if trusted is None:
            break
        if not trusted:
            return str(ip_address(value))
        last_hop = value
    # Só saltos conhecidos (ou lixo à esquerda deles): limita pelo último salto
    # válido. O endereço da conexão não serve: o uvicorn pode tê-lo copiado do
    # primeiro item do X-Forwarded-For, que o cliente controla.
    if last_hop is not None:
        return str(ip_address(last_hop))
    return request.client.host if request.client else "unknown"
