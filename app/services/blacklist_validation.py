import ipaddress
import socket
from typing import Optional
from fastapi import HTTPException, status

# Whitelist interna inmutable: IPs que NUNCA pueden ser bloqueadas
_PROTECTED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),     # Loopback
    ipaddress.ip_network("10.0.0.0/8"),      # RFC 1918 Clase A
    ipaddress.ip_network("172.16.0.0/12"),   # RFC 1918 Clase B
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918 Clase C
]

_PROTECTED_HOSTS = {
    "8.8.8.8",  # Google DNS primario
    "8.8.4.4",  # Google DNS secundario
    "1.1.1.1",  # Cloudflare DNS primario
    "1.0.0.1",  # Cloudflare DNS secundario
    "9.9.9.9",  # Quad9 DNS
}


def get_server_ip() -> Optional[str]:
    """Obtiene la IP local del propio servidor para protegerla."""
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return None


def _canonicalize(ip_str: str) -> ipaddress._BaseAddress:
    """
    Desempaqueta direcciones IPv4-mapeadas en IPv6 (::ffff:127.0.0.1 -> 127.0.0.1)
    para que restricciones y whitelist se apliquen de forma canónica e inmutable.
    """
    addr = ipaddress.ip_address(ip_str)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return addr


def validate_not_protected(ip: str) -> None:
    """
    Lanza HTTP 422 si la IP pertenece a rangos protegidos inmutables o no es global.
    Previene auto-denegación de servicio, bloqueos de infraestructura crítica y
    bypass por ortografías IPv6 mapeadas (CWE-158: denegación por canonización).
    """
    try:
        addr = _canonicalize(ip)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{ip}' no es una dirección IP válida.",
        )

    if str(addr) in _PROTECTED_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La IP '{ip}' es un servidor DNS público protegido y no puede ser bloqueada.",
        )

    # Bloqueo estricto de rangos no globales (loopback, RFC1918, link-local 169.254.0.0/16,
    # multicast, reservadas y no especificadas). Se listan propiedades de forma explícita
    # porque en CPython is_global puede ser True para IPv4 multicast (224.0.0.0/4).
    if (
        addr.is_loopback
        or addr.is_private
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
        or addr.is_reserved
        or not addr.is_global
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La IP '{ip}' es una dirección privada/loopback/link-local/multicast/reservada y no puede ser bloqueada.",
        )

    for net in _PROTECTED_NETWORKS:
        if addr in net:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"La IP '{ip}' pertenece a un rango privado/loopback (RFC 1918) protegido.",
            )

    srv_ip = get_server_ip()
    if srv_ip and str(addr) == srv_ip:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La IP '{ip}' corresponde al propio servidor. Bloquearla causaría auto-denegación de servicio.",
        )
