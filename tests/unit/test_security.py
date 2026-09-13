from app.core.security import hash_password, verify_password

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