from app.models.user_model import User
from app.core.security import verify_password, hash_password


def authenticate_user(db, email, password):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def process_password_recovery(db, email: str) -> None:
    """CWE-200: siempre silencioso. Genera token 1h y envía correo UDEC si existe."""
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.services.email_service import EmailService

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    EmailService.send_password_reset_email(email=user.email, token=token)


def reset_user_password(db, token: str, new_password: str) -> None:
    """Valida token, rota clave e invalida uso único."""
    from datetime import datetime, timezone

    from fastapi import HTTPException, status

    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido.",
        )
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres.",
        )

    user = db.query(User).filter(User.reset_token == token).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o ya utilizado.",
        )

    now = datetime.now(timezone.utc)
    expires = user.reset_token_expires
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token expirado. Solicita uno nuevo.",
            )

    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
