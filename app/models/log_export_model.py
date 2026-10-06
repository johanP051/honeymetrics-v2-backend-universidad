from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Date, DateTime
from app.db.base import Base


class LogExport(Base):
    """
    Modelo de Base de Datos para el historial persistente de exportaciones de logs crudos
    y trazabilidad de autorizaciones Human-in-the-Loop vía Telegram.
    """

    __tablename__ = "log_exports"

    id = Column(String(30), primary_key=True, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    date_range = Column(String(60), nullable=False)
    count = Column(Integer, nullable=False)
    status = Column(String(40), nullable=False, default="Procesando")
    file_format = Column(String(20), nullable=False, default="JSONL")
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
