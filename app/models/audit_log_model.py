from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from app.db.base import Base


class AuditLog(Base):
    """
    Tabla General de Auditoría para trazabilidad transversal de eventos de seguridad.
    Permite registrar operaciones de usuarios, analistas y triggers del motor SQL.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_email = Column(String(255), nullable=True)
    action = Column(String(80), nullable=False, index=True)
    entity_name = Column(String(80), nullable=False)
    entity_id = Column(String(64), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
