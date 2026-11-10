from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.blacklist_model import BlacklistEntry
from app.models.blacklist_vault_model import BlacklistAuditVault
from app.models.audit_log_model import AuditLog
from app.schemas.blacklist_schema import BlacklistEntryCreate, BlacklistEntryUpdate
from app.services.blacklist_validation import validate_not_protected


class BlacklistService:
    """Service Layer Pattern: Blacklist de IPs atacantes y Bóveda Forense."""

    _validate_not_protected = staticmethod(validate_not_protected)

    @staticmethod
    def _auto_status(score: int) -> str:
        return "Bloqueada" if score > 70 else "Monitoreada"

    @classmethod
    def get_all(cls, db: Session) -> List[BlacklistEntry]:
        return db.query(BlacklistEntry).order_by(BlacklistEntry.threat_score.desc()).all()

    @classmethod
    def get_by_id(cls, entry_id: int, db: Session) -> BlacklistEntry:
        entry = db.query(BlacklistEntry).filter(BlacklistEntry.id == entry_id).first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entrada de Blacklist con ID {entry_id} no encontrada.",
            )
        return entry

    @classmethod
    def get_vault(cls, db: Session, limit: int = 100, offset: int = 0) -> List[BlacklistAuditVault]:
        return (
            db.query(BlacklistAuditVault)
            .order_by(BlacklistAuditVault.deleted_at.desc())
            .offset(offset).limit(limit).all()
        )

    @classmethod
    def create(cls, payload: BlacklistEntryCreate, db: Session, admin_user_id: int) -> BlacklistEntry:
        validate_not_protected(payload.ip)
        existing = db.query(BlacklistEntry).filter(BlacklistEntry.ip == payload.ip).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La IP '{payload.ip}' ya está registrada en la Blacklist (ID: {existing.id}).",
            )
        entry = BlacklistEntry(
            ip=payload.ip, ip_type=payload.ip_type, country=payload.country,
            threat_score=payload.threat_score, category=payload.category,
            status=cls._auto_status(payload.threat_score), notes=payload.notes,
            blocked_by_user_id=admin_user_id, created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def update(cls, entry_id: int, payload: BlacklistEntryUpdate, db: Session) -> BlacklistEntry:
        entry = cls.get_by_id(entry_id, db)
        if payload.ip is not None and payload.ip != entry.ip:
            validate_not_protected(payload.ip)
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
    def delete(cls, entry_id: int, db: Session, deleted_by_user_id: Optional[int] = None) -> None:
        entry = cls.get_by_id(entry_id, db)
        snapshot = {
            "original_id": entry.id, "ip": entry.ip, "ip_type": entry.ip_type,
            "country": entry.country, "threat_score": entry.threat_score,
            "category": entry.category, "status": entry.status, "notes": entry.notes,
            "blocked_by_user_id": entry.blocked_by_user_id,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
        vault_entry = BlacklistAuditVault(
            original_entry_id=entry.id, original_ip=entry.ip, ip_type=entry.ip_type,
            country=entry.country, threat_score=entry.threat_score, category=entry.category,
            status=entry.status, notes=entry.notes,
            deleted_by_user_id=deleted_by_user_id or entry.blocked_by_user_id,
            full_record_json=snapshot, created_at=entry.created_at or datetime.now(timezone.utc),
            deleted_at=datetime.now(timezone.utc),
        )

        is_pg = False
        try:
            if db.bind and db.bind.dialect.name == "postgresql":
                is_pg = True
        except Exception:
            pass

        if not is_pg:
            db.add(vault_entry)

        audit_entry = AuditLog(
            actor_user_id=deleted_by_user_id, actor_email=None,
            action="BLACKLIST_IP_DELETED_APP", entity_name="blacklist_entries",
            entity_id=str(entry.id), details=snapshot, ip_address=entry.ip,
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        db.delete(entry)
        db.commit()

    delete_entry = delete
