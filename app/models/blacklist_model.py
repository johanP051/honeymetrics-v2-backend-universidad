from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.db.base import Base


class BlacklistEntry(Base):
    """
    Modelo ORM para el Threat Intelligence Center (Blacklist de IPs).

    Registra IPs marcadas como amenaza por el SOC. El status se calcula
    automáticamente en el Service Layer según el threat_score:
      - score > 70  → "Bloqueada"
      - score <= 70 → "Monitoreada"

    Trazabilidad: blocked_by_user_id guarda quién registró la entrada.
    """
    __tablename__ = "blacklist_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(45), unique=True, index=True, nullable=False)
    ip_type = Column(String(10), default="IPv4", nullable=False)
    country = Column(String(100), default="Unknown", nullable=False)
    threat_score = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)          # APT, Botnet, Scanner, Recon
    status = Column(String(30), nullable=False)            # Bloqueada | Monitoreada
    notes = Column(Text, nullable=True)

    # Trazabilidad de auditoría: qué usuario (admin) registró la entrada
    blocked_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
