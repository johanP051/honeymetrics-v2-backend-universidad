from app.models.user_model import User
from app.models.revoked_token_model import RevokedToken
from app.core.security import verify_password, hash_password, decode_access_token

def authenticate_user(db, email, password):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def revoke_token(db, token: str) -> None:
    """Revoca el JWT actual por jti (idempotente, port de guia)."""
    from datetime import datetime, timezone

    payload = decode_access_token(token)
    if not payload or "jti" not in payload:
        return
    exists = db.query(RevokedToken).filter(RevokedToken.token_jti == payload["jti"]).first()
    if exists:
        return
    exp = payload.get("exp")
    expires_at = (
        datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)
        if exp
        else datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(RevokedToken(token_jti=payload["jti"], expires_at=expires_at))
    db.commit()
