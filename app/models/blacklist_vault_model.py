from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from app.db.base import Base


class BlacklistAuditVault(Base):
    """
    Bóveda Forense Inmutable para registros eliminados de la Lista Negra (CTI).
    Garantiza el principio forense de No Repudio y trazabilidad histórica.
    """
    __tablename__ = "blacklist_audit_vault"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_entry_id = Column(Integer, nullable=False)
    original_ip = Column(String(45), index=True, nullable=False)
    ip_type = Column(String(10), nullable=True)
    country = Column(String(100), nullable=True)
    threat_score = Column(Integer, nullable=False)
    category = Column(String(50), nullable=True)
    status = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    deleted_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    full_record_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    deleted_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
