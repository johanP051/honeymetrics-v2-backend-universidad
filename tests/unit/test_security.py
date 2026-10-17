from app.core.security import hash_password, verify_password, create_access_token

import jwt
from app.core.config import settings


def test_password_incorrect():
    hashed = hash_password("Testing")
    assert not verify_password("Testing123", hashed)  # not: si devuelve False entonces la prueba pasa


def test_password_correct():
    hashed = hash_password("Test123")
    assert verify_password("Test123", hashed)


def test_hashes_are_different():
    first_hash = hash_password("Prueba1234")
    second_hash = hash_password("Prueba1234")

    assert first_hash != second_hash


def test_require_admin_accepts_seed_role_name_admin():
    """El rol semilla 'admin' (create_admin.py) debe pasar el guard RBAC."""
    from unittest.mock import MagicMock
    from app.api.deps import require_admin_user

    user = MagicMock()
    user.role_id = 4
    role = MagicMock()
    role.name = "admin"
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = role

    assert require_admin_user(current_user=user, db=db) is user


def test_require_admin_rejects_non_admin_role():
    """Un rol no administrador debe recibir HTTP 403."""
    from unittest.mock import MagicMock
    import pytest
    from fastapi import HTTPException
    from app.api.deps import require_admin_user

    user = MagicMock()
    user.role_id = 2
    role = MagicMock()
    role.name = "analista"
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = role

    with pytest.raises(HTTPException) as exc_info:
        require_admin_user(current_user=user, db=db)

    assert exc_info.value.status_code == 403


def test_access_token_contains_user_id():
    token = create_access_token("15")

    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    assert payload["sub"] == "15"
    assert "exp" in payload


def test_require_admin_accepts_case_variants():
    """'ADMINISTRADOR' y ' Admin ' con espacios también son admin."""
    from unittest.mock import MagicMock
    from app.api.deps import require_admin_user

    for name in ("ADMINISTRADOR", " Admin ", "Administrador"):
        user = MagicMock()
        role = MagicMock()
        role.name = name
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = role
        assert require_admin_user(current_user=user, db=db) is user


def test_require_admin_rejects_missing_role():
    """Rol inexistente en BD debe recibir HTTP 403."""
    from unittest.mock import MagicMock
    import pytest
    from fastapi import HTTPException
    from app.api.deps import require_admin_user

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        require_admin_user(current_user=MagicMock(), db=db)

    assert exc_info.value.status_code == 403


def test_email_templates_contain_logo_and_no_reply_disclaimer():
    """Verifica que las plantillas de correo incluyan el logo circular oficial y el aviso de no responder."""
    from unittest.mock import patch
    from app.services.email_service import EmailService

    with patch("app.core.config.settings.RESEND_API_KEY", "re_test_key_123"):
        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "mock_id"}

            # Plantilla recuperación de contraseña
            EmailService.send_password_reset_email("investigador@ucundinamarca.edu.co", "sample_reset_token")
            assert mock_send.call_count == 1
            call_params_reset = mock_send.call_args[0][0]
            html_reset = call_params_reset["html"]
            assert "HoneyMetrics_logo_circled" in html_reset
            assert "no respondas a este mensaje" in html_reset

            mock_send.reset_mock()

            # Plantilla bienvenida de usuario
            EmailService.send_welcome_email("nuevo@ucundinamarca.edu.co", "TemporalKey*123")
            assert mock_send.call_count == 1
            call_params_welcome = mock_send.call_args[0][0]
            html_welcome = call_params_welcome["html"]
            assert "HoneyMetrics_logo_circled" in html_welcome
            assert "no respondas a este mensaje" in html_welcome


def test_security_headers_present():
    """Verifica que el middleware HTTP inyecte cabeceras de seguridad defensivas en todas las respuestas."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "max-age=31536000; includeSubDomains" in response.headers["strict-transport-security"]

