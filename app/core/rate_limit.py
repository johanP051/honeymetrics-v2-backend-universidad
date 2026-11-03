"""
Rate Limiting con slowapi protegido contra spoofing de cabeceras de proxy.
Puerto del backend guía (honeymetrics-backend/app/core/rate_limit.py) al
backend académico: usa TRUSTED_PROXY_CIDRS para determinar el salt de proxy
de confianza y solo confía en CF-Connecting-IP / X-Forwarded-For desde
peers previamente validados (anti-spoofing de X-Forwarded-For).
"""
import ipaddress

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
from app.core.config import settings


def _parse_ip(value: str):
    try:
        return ipaddress.ip_address(value.strip())
    except (ValueError, AttributeError):
        return None


def _trusted_networks():
    networks = []
    for cidr in settings.TRUSTED_PROXY_CIDRS:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            continue
    return networks


def _is_trusted(ip, networks) -> bool:
    return ip is not None and any(ip.version == network.version and ip in network for network in networks)


def get_real_client_ip(request: Request) -> str:
    """
    Obtiene la IP real del cliente considerando cabeceras de proxy reverso
    y Cloudflare Tunnel (CF-Connecting-IP, X-Forwarded-For).
    """
    peer = _parse_ip(request.client.host) if request.client else None
    fallback = str(peer) if peer else get_remote_address(request)
    networks = _trusted_networks()
    if not _is_trusted(peer, networks):
        return fallback

    forwarded = request.headers.get("cf-connecting-ip")
    if forwarded:
        client_ip = _parse_ip(forwarded)
        if client_ip:
            return str(client_ip)

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        chain = [_parse_ip(value) for value in forwarded_for.split(",")]
        if chain and all(chain):
            # Quita proxies confiables desde el salto más cercano y usa el primer cliente no confiable.
            for candidate in reversed(chain):
                if not _is_trusted(candidate, networks):
                    return str(candidate)
            return str(chain[0])
    return fallback


limiter = Limiter(key_func=get_real_client_ip)


def setup_rate_limiting(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
