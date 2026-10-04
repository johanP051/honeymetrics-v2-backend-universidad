from passlib.context import CryptContext

from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") # crea un admin de contrasenas llamado pwd_context y se configura para generar y verificar hashes usando Argon2

def hash_password(password: str) -> str:
    hashed_password = pwd_context.hash(password)
    return hashed_password

def verify_password(password: str, hashed_password: str) -> bool:
    passwd_validation = pwd_context.verify(password, hashed_password)
    return passwd_validation

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "exp": expire
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
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
