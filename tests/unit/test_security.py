from app.core.security import hash_password, verify_password, create_access_token

import jwt
from app.core.config import settings

def test_password_incorrect():
    hashed = hash_password("Testing")
    assert not verify_password("Testing123", hashed) #not: si devuelve False entonces la prueba pasa

def test_password_correct():
    hashed = hash_password("Test123")
    assert verify_password("Test123", hashed)

def test_hashes_are_different():
    first_hash = hash_password("Prueba1234")
    second_hash = hash_password("Prueba1234")

    assert first_hash != second_hash

def test_access_token_contains_user_id():
    token = create_access_token("15")

    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    assert payload["sub"] == "15"
    assert "exp" in payload