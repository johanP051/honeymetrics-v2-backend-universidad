from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class MFABackupCode(Base):
    """
    Modelo ORM para códigos de respaldo 2FA (OWASP ASVS V2.8).
    Almacena únicamente el hash SHA-256 de los 8 códigos de recuperación de un solo uso.
    """
    __tablename__ = "mfa_backup_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_hash = Column(String(64), nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="backup_codes")
