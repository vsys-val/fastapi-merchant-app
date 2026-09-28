"""Regra do IP do cliente com as cadeias medidas em produção (ADR-0016)."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.client_ip import client_ip
from app.config import Settings

CLIENT = "132.196.6.76"
# Medido pelo workflow "Network check" em 2026-09-28.
DIRECT = f"{CLIENT}, 162.158.79.42, 10.31.64.171"
THROUGH_SITE = f"{CLIENT}, 108.162.245.13, 108.162.245.13, 74.220.48.207, 162.158.79.42, 10.31.64.171"


def _request(forwarded: str | None, *, peer: str = "10.31.64.171", trusted: str = "74.220.48.0/24") -> Request:
    headers = [] if forwarded is None else [(b"x-forwarded-for", forwarded.encode())]
    app = SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(trusted_proxy_networks=trusted)))
    return Request({"type": "http", "headers": headers, "client": (peer, 1234), "app": app})


@pytest.mark.parametrize("chain", [DIRECT, THROUGH_SITE], ids=["direto", "pelo-site"])
def test_finds_the_client_on_both_measured_paths(chain):
    assert client_ip(_request(chain)) == CLIENT


@pytest.mark.parametrize("chain", [DIRECT, THROUGH_SITE], ids=["direto", "pelo-site"])
def test_a_forged_forwarded_for_does_not_change_the_address(chain):
    # O cliente envia o próprio X-Forwarded-For; a Cloudflare acrescenta o real depois.
    assert client_ip(_request(f"1.2.3.4, 5.6.7.8, {chain}")) == CLIENT
    assert client_ip(_request(f"lixo, {chain}")) == CLIENT


def test_an_unknown_site_egress_limits_by_that_hop_instead_of_trusting_the_left():
    # Se a saída do site mudar para fora da rede configurada, todo o tráfego do site
    # divide o limite desse salto: mais restritivo, nunca contornável.
    chain = f"{CLIENT}, 108.162.245.13, 108.162.245.13, 74.220.48.207, 162.158.79.42, 10.31.64.171"
    assert client_ip(_request(chain, trusted="")) == "74.220.48.207"


def test_without_proxy_headers_uses_the_connection_address():
    assert client_ip(_request(None, peer="127.0.0.1")) == "127.0.0.1"


def test_only_known_hops_limits_by_the_leftmost_valid_hop():
    assert client_ip(_request("garbage, 162.158.79.42, 10.31.64.171", peer="9.9.9.9")) == "162.158.79.42"


def test_ipv6_clients_are_normalized():
    assert client_ip(_request("2804:14C:0:0::1, 162.158.79.42, 10.31.64.171")) == "2804:14c::1"


def test_trusted_networks_setting_rejects_invalid_cidr(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:password@localhost/test_db")
    monkeypatch.setenv("JWT_SECRET", "test-only-" + "x" * 40)
    monkeypatch.setenv("TRUSTED_PROXY_NETWORKS", "74.220.48.0/24, não-é-rede")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
