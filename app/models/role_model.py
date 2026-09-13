from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True) #index: aumenta la velocidad si el campo se usa constatemente para filtros, pero ralentiza opoeraciones DML
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(50), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
