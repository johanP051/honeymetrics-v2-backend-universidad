import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

def test_login_request_accepts_valid_data():
    login_request = LoginRequest(
        email="correo@prueba.com",
        password="Testing",
    )

    assert str(login_request.email) == "correo@prueba.com"
    assert login_request.password == "Testing"


def test_login_request_rejects_invalid_email():
    with pytest.raises(ValidationError):
        LoginRequest(
            email="correo-invalido",
            password="Testing",
        )

def test_login_request_requires_email():
    with pytest.raises(ValidationError):
        LoginRequest(password="Testing")


def test_login_request_requires_password():
    with pytest.raises(ValidationError):
        LoginRequest(email="correo@prueba.com")


def test_token_response_defaults_to_bearer():
    token_response = TokenResponse(access_token="signed-token")

    assert token_response.access_token == "signed-token"
    assert token_response.token_type == "bearer"


def test_token_response_rejects_unknown_token_type():
    with pytest.raises(ValidationError):
        TokenResponse(access_token="signed-token", token_type="basic")


def test_user_response_excludes_sensitive_password_hash():
    user_response = UserResponse(
        id=15,
        email="correo@prueba.com",
        first_names="Usuario",
        last_names="Prueba",
        role_id=1,
        is_active=True,
        must_change_password=False,
    )

    assert user_response.email == "correo@prueba.com"
    assert "hashed_password" not in user_response.model_dump()


def test_token_response_accepts_user_response():
    user_response = UserResponse(
        id=1,
        email="correo@prueba.com",
        first_names="Usuario",
        last_names="Prueba",
        role_id=1,
        is_active=True,
        must_change_password=False,
    )
    token_response = TokenResponse(
        access_token="signed-token",
        user=user_response,
    )

    assert token_response.user is not None
    assert token_response.user.email == "correo@prueba.com"