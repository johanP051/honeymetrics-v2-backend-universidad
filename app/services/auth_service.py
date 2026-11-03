"""
Servicio de Autenticación, recuperación y revocación de credenciales.
HoneyMetrics Backend v2.0 (Cátedra de Ingeniería de Software - UDEC)
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.domain_errors import ValidationError
from app.core.password_policy import validate_new_password
from app.core.security import decode_access_token, hash_password, verify_password
from app.models.revoked_token_model import RevokedToken
from app.models.user_model import User
from app.services.email_service import EmailService

# Hash estático precalculado para hardening contra timing attacks (CWE-208)
_DUMMY_TIMING_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RdescudvJCsgqlfreOJAcw"


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Autentica usuario con protección contra ataques de temporización (anti-enumeración)."""
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        verify_password(password, _DUMMY_TIMING_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def revoke_token(db: Session, token: str) -> None:
    """Revoca el JWT actual por su jti (idempotente)."""
    payload = decode_access_token(token)
    if not payload or "jti" not in payload:
        return
    jti = payload["jti"]
    if db.query(RevokedToken).filter(RevokedToken.token_jti == jti).first():
        return
    exp = payload.get("exp")
    expires_at = (
        datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)
        if exp
        else datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(RevokedToken(token_jti=jti, expires_at=expires_at))
    db.commit()


def process_password_recovery(db: Session, email: str) -> None:
    """CWE-200: anti-enumeración. Si el correo existe, genera token de 1h y envía correo."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    EmailService.send_password_reset_email(email=user.email, token=token)


def reset_user_password(db: Session, token: str, new_password: str) -> None:
    """Valida token, rota contraseña (OWASP ASVS V2.1) e incrementa auth_version."""
    if not token or not token.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido.")

    try:
        validated_pwd = validate_new_password(new_password)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    user = db.query(User).filter(User.reset_token == token).first()
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido o ya utilizado.")

    now = datetime.now(timezone.utc)
    expires = user.reset_token_expires
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token expirado. Solicita uno nuevo.")

    user.hashed_password = hash_password(validated_pwd)
    user.reset_token = None
    user.reset_token_expires = None
    user.must_change_password = False
    user.auth_version = int(user.auth_version or 0) + 1
    db.commit()
