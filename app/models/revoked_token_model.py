from app.db.base import Base
from sqlalchemy import Column, Integer, String, DateTime


class RevokedToken(Base):
    """Denylist de JWT revocados por logout (port de guia)."""

    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_jti = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
