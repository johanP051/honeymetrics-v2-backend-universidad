"""Utilidad compartida para resolver el origen del frontend desde una petición HTTP."""
from urllib.parse import urlparse
from fastapi import Request

from app.core.config import settings


def resolve_request_origin(request: Request) -> str:
    """Extrae el origen dinámico de la petición (Origin o Referer) con fallback a settings.FRONTEND_URL."""
    origin = request.headers.get("origin")
    if origin and origin.strip() and origin.strip().lower() != "null":
        return origin.strip().rstrip("/")

    referer = request.headers.get("referer")
    if referer and referer.strip():
        parsed = urlparse(referer.strip())
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    return settings.FRONTEND_URL.rstrip("/")
