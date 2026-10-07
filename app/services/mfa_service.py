"""Servicio 2FA-OTP (PB-HM-07.1, port de guia)."""

import io
import logging
from datetime import timedelta

import pyotp
import qrcode
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token
from app.models.user_model import User

logger = logging.getLogger(__name__)


def setup_mfa(db: Session, user: User) -> dict:
    """Genera secreto TOTP + QR para Google Authenticator."""
    secret = pyotp.random_base32()
    user.totp_secret = secret
    db.commit()

    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="HoneyMetrics UDEC")
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    import base64

    qr = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"secret": secret, "qr": qr}


def verify_and_enable_mfa(db: Session, user: User, code: str) -> None:
    """Valida codigo de 6 digitos y activa 2FA."""
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes generar el secreto primero con /mfa/setup.",
        )
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo incorrecto. Intenta de nuevo.",
        )
    user.is_mfa_enabled = True
    db.commit()


def disable_mfa(db: Session, user: User) -> None:
    user.is_mfa_enabled = False
    user.totp_secret = None
    db.commit()


def mfa_login_flow(db: Session, user: User) -> dict:
    """Retorna mfa_required + token temporal de 5 min si 2FA activo."""
    if not user.is_mfa_enabled or not user.totp_secret:
        return {"mfa_required": False}
    mfa_token = create_access_token(
        subject=f"mfa:{user.id}",
        expires_delta=timedelta(minutes=5),
    )
    return {"mfa_required": True, "mfa_token": mfa_token}


def verify_login_mfa(db: Session, mfa_token: str, code: str) -> User:
    """Valida OTP contra el usuario del mfa_token y lo devuelve."""
    payload = decode_access_token(mfa_token)
    if not payload or not payload.get("sub", "").startswith("mfa:"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token MFA invalido o expirado.",
        )
    user_id = int(payload["sub"].split(":", 1)[1])
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_mfa_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA no esta configurado para este usuario.",
        )
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Codigo MFA incorrecto.",
        )
    return user
