from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base


class Role(Base):
    """
    Catálogo de roles para el control de acceso basado en roles (RBAC).
    Módulo 1: Seguridad, Autenticación y Autorización.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relación inversa: Un rol tiene muchos usuarios (1:N)
    users = relationship("User", back_populates="role", cascade="all, delete-orphan")
