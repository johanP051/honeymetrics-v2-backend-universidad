import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    Fernet = None
    InvalidToken = Exception
    _HAS_CRYPTOGRAPHY = False

from passlib.context import CryptContext
import jwt
from app.core.config import settings

# Gestor de contraseñas con Argon2 (inmune al límite de 72 bytes)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Genera hash seguro de contraseña usando Argon2."""
    return pwd_context.hash(password)


get_password_hash = hash_password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash Argon2."""
    return pwd_context.verify(plain_password, hashed_password)


def _get_fernet() -> Optional[object]:
    """Genera o retorna instancia de Fernet derivada determinísticamente de SECRET_KEY."""
    if not _HAS_CRYPTOGRAPHY or Fernet is None:
        return None
    secret_bytes = settings.SECRET_KEY.encode("utf-8")
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(secret_bytes).digest())
    return Fernet(derived_key)


def encrypt_totp_secret(secret: str) -> str:
    """Cifra el secreto TOTP en reposo usando Fernet derivado de SECRET_KEY."""
    if not secret:
        return secret
    fernet = _get_fernet()
    if fernet is None:
        return secret
    return fernet.encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_totp_secret(token: str) -> str:
    """
    Descifra el secreto TOTP. Si ya es texto base32 plano (legacy) o no hay Fernet,
    captura la excepción y lo retorna directamente para compatibilidad retroactiva.
    """
    if not token:
        return token
    fernet = _get_fernet()
    if fernet is None:
        return token
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return token


def create_access_token(
    subject: Union[str, int, dict],
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[list[str]] = None,
    auth_version: int = 0,
    mfa_pending: bool = False,
) -> str:
    """
    Genera un JWT firmado con HS256. Soporta subject como str/int o dict de payload.
    Incluye jti único, exp, scopes, auth_version y opcionalmente mfa_pending.
    """
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    if isinstance(subject, dict):
        to_encode = subject.copy()
        to_encode.setdefault("exp", expire)
        to_encode.setdefault("jti", uuid.uuid4().hex)
        if scopes is not None:
            to_encode["scopes"] = scopes
        elif "scopes" not in to_encode:
            to_encode["scopes"] = []
        if "auth_version" not in to_encode:
            to_encode["auth_version"] = auth_version
        if mfa_pending:
            to_encode["mfa_pending"] = True
    else:
        to_encode = {
            "sub": str(subject),
            "exp": expire,
            "jti": uuid.uuid4().hex,
            "scopes": scopes or [],
            "auth_version": auth_version,
        }
        if mfa_pending:
            to_encode["mfa_pending"] = True

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT. Retorna el payload si es válido,
    o None si el token es inválido, expirado o malformado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
