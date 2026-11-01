import ipaddress
import socket
from typing import Optional
from fastapi import HTTPException, status

# Whitelist interna inmutable: IPs que NUNCA pueden ser bloqueadas
_PROTECTED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),    # Loopback
    ipaddress.ip_network("10.0.0.0/8"),     # RFC 1918 Clase A
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


def validate_not_protected(ip: str) -> None:
    """
    Lanza HTTP 422 si la IP pertenece a rangos protegidos inmutables.
    Previene auto-denegación de servicio y bloqueos de infraestructura crítica.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{ip}' no es una dirección IP válida.",
        )

    if ip in _PROTECTED_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La IP '{ip}' es un servidor DNS público protegido y no puede ser bloqueada.",
        )

    for net in _PROTECTED_NETWORKS:
        if addr in net:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"La IP '{ip}' pertenece a un rango privado/loopback (RFC 1918) protegido.",
            )

    srv_ip = get_server_ip()
    if srv_ip and ip == srv_ip:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La IP '{ip}' corresponde al propio servidor. Bloquearla causaría auto-denegación de servicio.",
        )
