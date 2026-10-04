"""
BlacklistService — Service Layer para el Threat Intelligence Center.

Invariantes de Dominio:
  1. Unicidad de IP: ninguna IP puede registrarse dos veces.
  2. Whitelist interna inmutable: IPs de RFC 1918, loopback y DNS públicos
     críticos nunca pueden ser marcadas como "Bloqueada" (prevención de auto-denegación
     de servicio y bloqueo accidental de infraestructura).
  3. Auto-cálculo de status: si score > 70 → "Bloqueada", si no → "Monitoreada".
  4. Trazabilidad: toda entrada registra el ID del administrador que la creó.
"""
import ipaddress
import socket
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.blacklist_model import BlacklistEntry
from app.schemas.blacklist_schema import BlacklistEntryCreate, BlacklistEntryUpdate


# Whitelist interna inmutable: IPs que NUNCA pueden ser bloqueadas
_PROTECTED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),    # Loopback
    ipaddress.ip_network("10.0.0.0/8"),     # RFC 1918 Clase A
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918 Clase B
    ipaddress.ip_network("192.168.0.0/16"), # RFC 1918 Clase C
]

_PROTECTED_HOSTS = {
    "8.8.8.8",    # Google DNS primario
    "8.8.4.4",    # Google DNS secundario
    "1.1.1.1",    # Cloudflare DNS primario
    "1.0.0.1",    # Cloudflare DNS secundario
    "9.9.9.9",    # Quad9 DNS
}


def _get_server_ip() -> Optional[str]:
    """Obtiene la IP local del propio servidor para protegerla."""
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return None


class BlacklistService:
    """
    Service Layer Pattern: Contiene la lógica de negocio completa del
    Threat Intelligence Center (Blacklist de IPs atacantes).
    """

    @staticmethod
    def _validate_not_protected(ip: str) -> None:
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

        server_ip = _get_server_ip()
        if server_ip and ip == server_ip:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"La IP '{ip}' corresponde al propio servidor. Bloquearla causaría auto-denegación de servicio.",
            )

    @staticmethod
    def _auto_status(score: int) -> str:
        """Calcula el status automático según el umbral de threat score."""
        return "Bloqueada" if score > 70 else "Monitoreada"

    @classmethod
    def get_all(cls, db: Session) -> List[BlacklistEntry]:
        """Retorna todas las entradas ordenadas por threat_score descendente."""
        return (
            db.query(BlacklistEntry)
            .order_by(BlacklistEntry.threat_score.desc())
            .all()
        )

    @classmethod
    def get_by_id(cls, entry_id: int, db: Session) -> BlacklistEntry:
        """Obtiene una entrada por ID o lanza HTTP 404."""
        entry = db.query(BlacklistEntry).filter(BlacklistEntry.id == entry_id).first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entrada de Blacklist con ID {entry_id} no encontrada.",
            )
        return entry

    @classmethod
    def create(
        cls,
        payload: BlacklistEntryCreate,
        db: Session,
        admin_user_id: int,
    ) -> BlacklistEntry:
        """
        Registra una nueva IP en la Blacklist aplicando todas las invariantes:
          1. Valida que la IP no sea protegida.
          2. Valida unicidad de IP.
          3. Auto-calcula el status según el score.
          4. Registra la trazabilidad del admin.
        """
        cls._validate_not_protected(payload.ip)

        existing = db.query(BlacklistEntry).filter(BlacklistEntry.ip == payload.ip).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La IP '{payload.ip}' ya está registrada en la Blacklist (ID: {existing.id}).",
            )

        entry = BlacklistEntry(
            ip=payload.ip,
            ip_type=payload.ip_type,
            country=payload.country,
            threat_score=payload.threat_score,
            category=payload.category,
            status=cls._auto_status(payload.threat_score),
            notes=payload.notes,
            blocked_by_user_id=admin_user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def update(
        cls,
        entry_id: int,
        payload: BlacklistEntryUpdate,
        db: Session,
    ) -> BlacklistEntry:
        """
        Actualiza campos de una entrada existente. Si cambia la IP,
        re-valida protecciones y unicidad. Si cambia el score, recalcula el status.
        """
        entry = cls.get_by_id(entry_id, db)

        if payload.ip is not None and payload.ip != entry.ip:
            cls._validate_not_protected(payload.ip)
            duplicate = db.query(BlacklistEntry).filter(BlacklistEntry.ip == payload.ip).first()
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"La IP '{payload.ip}' ya está registrada en la Blacklist.",
                )
            entry.ip = payload.ip

        if payload.ip_type is not None:
            entry.ip_type = payload.ip_type
        if payload.country is not None:
            entry.country = payload.country
        if payload.category is not None:
            entry.category = payload.category
        if payload.notes is not None:
            entry.notes = payload.notes

        if payload.threat_score is not None:
            entry.threat_score = payload.threat_score
            entry.status = cls._auto_status(entry.threat_score)
        elif payload.status is not None:
            entry.status = payload.status

        entry.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def delete(cls, entry_id: int, db: Session) -> None:
        """Elimina permanentemente una entrada de la Blacklist."""
        entry = cls.get_by_id(entry_id, db)
        db.delete(entry)
        db.commit()
