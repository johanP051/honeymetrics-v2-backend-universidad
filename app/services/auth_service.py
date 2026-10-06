from app.models.user_model import User
from app.core.security import verify_password


def authenticate_user(db, email, password):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
