"""
AuditService — Capa de servicio para registro y consulta de auditoría.
HoneyMetrics Backend v2.0 (UDEC)
"""
from typing import Any, List, Optional
from sqlalchemy.orm import Session
from app.models.audit_log_model import AuditLog


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        action: str,
        entity_name: str,
        actor_user_id: Optional[int] = None,
        actor_email: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Any] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Registra un evento de seguridad o modificación en audit_logs."""
        entry = AuditLog(
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(entry)
        return entry

    @staticmethod
    def list_logs(
        db: Session, limit: int = 100, offset: int = 0
    ) -> List[AuditLog]:
        """Consulta registros de auditoría ordenados descendentemente por fecha."""
        return (
            db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
