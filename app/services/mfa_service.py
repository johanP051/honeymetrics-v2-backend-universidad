"""
Servicio 2FA-OTP con Fernet en reposo, 8 códigos de respaldo SHA-256 y anti-replay.
HoneyMetrics Backend v2.0 (Cátedra de Ingeniería de Software - UDEC)
"""
import base64
import hashlib
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import List

import pyotp
import qrcode
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import get_scopes_for_role
from app.core.security import (
    create_access_token,
    decode_access_token,
    decrypt_totp_secret,
    encrypt_totp_secret,
)
from app.models.audit_log_model import AuditLog
from app.models.mfa_backup_code_model import MFABackupCode
from app.models.revoked_token_model import RevokedToken
from app.models.user_model import User


def _generate_backup_codes(count: int = 8) -> List[str]:
    """Genera códigos criptográficos de respaldo en formato XXXX-XXXX."""
    return [f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}" for _ in range(count)]


def setup_mfa(db: Session, user: User) -> dict:
    """Genera o reutiliza secreto TOTP + QR para Google Authenticator (idempotente)."""
    if not user.is_mfa_enabled and user.totp_secret:
        secret = decrypt_totp_secret(user.totp_secret)
    else:
        secret = pyotp.random_base32()
        user.totp_secret = encrypt_totp_secret(secret)
        db.commit()

    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="HoneyMetrics UDEC")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"secret": secret, "qr": qr}


def verify_and_enable_mfa(db: Session, user: User, code: str) -> dict:
    """Valida código TOTP con valid_window=1, genera 8 códigos de respaldo y emite nuevo JWT."""
    if not user.totp_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debes generar el secreto primero con /mfa/setup.")
    decrypted_secret = decrypt_totp_secret(user.totp_secret)
    totp = pyotp.TOTP(decrypted_secret)
    if not totp.verify(code.strip(), valid_window=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Codigo incorrecto. Intenta de nuevo.")

    db.query(MFABackupCode).filter(MFABackupCode.user_id == user.id).delete()
    backup_codes = _generate_backup_codes(8)
    for raw_code in backup_codes:
        chash = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
        db.add(MFABackupCode(user_id=user.id, code_hash=chash))

    user.is_mfa_enabled = True
    user.auth_version = int(user.auth_version or 0) + 1
    db.add(AuditLog(
        actor_user_id=user.id, actor_email=user.email,
        action="MFA_ENABLED", entity_name="users", entity_id=str(user.id),
        details={"backup_codes_count": 8},
    ))
    db.commit()
    db.refresh(user)

    role_name = user.role.name if getattr(user, "role", None) else None
    user_scopes = get_scopes_for_role(role_name)
    new_token = create_access_token(
        str(user.id),
        scopes=user_scopes,
        auth_version=user.auth_version,
        role=role_name,
    )
    return {
        "message": "Autenticación de dos factores (2FA) activada correctamente.",
        "backup_codes": backup_codes,
        "access_token": new_token,
        "token_type": "bearer",
    }


def disable_mfa(db: Session, user: User) -> dict:
    """Desactiva 2FA, purga códigos de respaldo, incrementa auth_version y emite nuevo JWT."""
    db.query(MFABackupCode).filter(MFABackupCode.user_id == user.id).delete()
    user.is_mfa_enabled = False
    user.totp_secret = None
    user.auth_version = int(user.auth_version or 0) + 1
    db.add(AuditLog(
        actor_user_id=user.id, actor_email=user.email,
        action="MFA_DISABLED", entity_name="users", entity_id=str(user.id),
        details={"status": "disabled"},
    ))
    db.commit()
    db.refresh(user)

    role_name = user.role.name if getattr(user, "role", None) else None
    user_scopes = get_scopes_for_role(role_name)
    new_token = create_access_token(
        str(user.id),
        scopes=user_scopes,
        auth_version=user.auth_version,
        role=role_name,
    )
    return {
        "message": "Autenticación de dos factores (2FA) desactivada.",
        "access_token": new_token,
        "token_type": "bearer",
    }


def mfa_login_flow(db: Session, user: User) -> dict:
    """Retorna mfa_required + token temporal de 5 min si 2FA activo."""
    if not user.is_mfa_enabled or not user.totp_secret:
        return {"mfa_required": False}
    mfa_token = create_access_token(subject=f"mfa:{user.id}", expires_delta=timedelta(minutes=5), mfa_pending=True)
    return {"mfa_required": True, "mfa_token": mfa_token}


def verify_login_mfa(db: Session, mfa_token: str, code: str) -> User:
    """Valida OTP o código de respaldo contra mfa_token consumiendo jti para anti-replay."""
    payload = decode_access_token(mfa_token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token MFA invalido o expirado.")

    sub_str = str(payload.get("sub", ""))
    if not sub_str.startswith("mfa:") and not payload.get("mfa_pending"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token MFA invalido o expirado.")

    jti = payload.get("jti")
    if jti:
        if db.query(RevokedToken).filter(RevokedToken.token_jti == jti).first():
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token MFA ya ha sido utilizado.")
        exp = payload.get("exp")
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None) if exp else datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(RevokedToken(token_jti=jti, expires_at=exp_dt))
        db.commit()

    user_id = int(sub_str.split(":", 1)[1]) if sub_str.startswith("mfa:") else int(sub_str)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_mfa_enabled or not user.totp_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA no esta configurado para este usuario.")

    decrypted_secret = decrypt_totp_secret(user.totp_secret)
    if pyotp.TOTP(decrypted_secret).verify(code.strip(), valid_window=1):
        return user

    clean_code = code.strip().upper()
    if len(clean_code) == 8 and "-" not in clean_code:
        clean_code = f"{clean_code[:4]}-{clean_code[4:]}"
    chash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()
    backup_code = db.query(MFABackupCode).filter(
        MFABackupCode.user_id == user.id,
        MFABackupCode.code_hash == chash,
        MFABackupCode.used_at.is_(None),
    ).first()
    if not backup_code:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Codigo MFA o de respaldo incorrecto.")

    backup_code.used_at = datetime.now(timezone.utc)
    db.add(AuditLog(
        actor_user_id=user.id, actor_email=user.email,
        action="MFA_BACKUP_CODE_USED", entity_name="mfa_backup_codes",
        entity_id=str(backup_code.id), details={"code_id": backup_code.id},
    ))
    db.commit()
    return user
