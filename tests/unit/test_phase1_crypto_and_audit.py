from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import User, Role, AuditLog, BlacklistAuditVault, MFABackupCode
from app.core.password_policy import validate_new_password, normalize_password
from app.core.domain_errors import ValidationError
from app.core.security import (
    encrypt_totp_secret,
    decrypt_totp_secret,
    create_access_token,
    decode_access_token,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(bind=engine)


def test_password_policy_validation():
    valid = validate_new_password("MiClaveRobusta2026!#")
    assert valid == "MiClaveRobusta2026!#"

    # Normalización de espacios
    assert normalize_password("  clave   con   espacios  ") == "clave con espacios"

    # Longitud mínima
    with pytest.raises(ValidationError, match="al menos 12 caracteres"):
        validate_new_password("corta123")

    # Longitud máxima
    with pytest.raises(ValidationError, match="exceder los 128 caracteres"):
        validate_new_password("A" * 129)

    # Denylist
    with pytest.raises(ValidationError, match="demasiado común"):
        validate_new_password("password12345")

    # Caracteres repetidos
    with pytest.raises(ValidationError, match="mismo carácter repetido"):
        validate_new_password("bbbbbbbbbbbb")

    # No repetición de clave actual
    with pytest.raises(ValidationError, match="igual a la contraseña actual"):
        validate_new_password("MismaClave123!", current_password="MismaClave123!")


def test_fernet_crypto_totp():
    secret = "JBSWY3DPEHPK3PXP"
    encrypted = encrypt_totp_secret(secret)
    assert encrypted != secret
    assert len(encrypted) > 50

    decrypted = decrypt_totp_secret(encrypted)
    assert decrypted == secret

    # Fallback transparente para texto plano legacy o vacío
    assert decrypt_totp_secret("") == ""
    assert decrypt_totp_secret("LEGACYPLAINSECRET") == "LEGACYPLAINSECRET"


def test_jwt_auth_version_and_mfa_pending():
    # Token normal con auth_version
    token = create_access_token(subject=42, auth_version=3, scopes=["logs:read"])
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["auth_version"] == 3
    assert payload["scopes"] == ["logs:read"]
    assert "mfa_pending" not in payload

    # Token MFA pendiente
    mfa_token = create_access_token(subject="mfa:42", mfa_pending=True)
    mfa_payload = decode_access_token(mfa_token)
    assert mfa_payload is not None
    assert mfa_payload["mfa_pending"] is True

    # Token con dict payload
    dict_token = create_access_token(subject={"sub": "99", "custom": "field"})
    dict_payload = decode_access_token(dict_token)
    assert dict_payload["sub"] == "99"
    assert dict_payload["custom"] == "field"


def test_audit_and_vault_models(db_session: Session):
    # Registrar log en audit_logs
    log = AuditLog(
        actor_user_id=1,
        actor_email="admin@honeymetrics.com",
        action="TEST_ACTION",
        entity_name="users",
        entity_id="1",
        details={"ip": "1.2.3.4"},
        ip_address="1.2.3.4",
    )
    db_session.add(log)
    db_session.commit()
    assert log.id is not None

    # Registrar en blacklist_audit_vault
    vault_entry = BlacklistAuditVault(
        original_entry_id=10,
        original_ip="185.220.101.77",
        ip_type="IPv4",
        country="Germany",
        threat_score=88,
        category="APT",
        status="Bloqueada",
        full_record_json={"ip": "185.220.101.77", "threat_score": 88},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(vault_entry)
    db_session.commit()
    assert vault_entry.id is not None
    assert vault_entry.full_record_json["threat_score"] == 88


def test_user_backup_codes_cascade(db_session: Session):
    role = Role(name="Analista", description="Rol analista")
    db_session.add(role)
    db_session.commit()

    user = User(
        email="test_cascade@ucundinamarca.edu.co",
        first_names="Ana",
        last_names="García",
        hashed_password="hash",
        role_id=role.id,
        auth_version=1,
    )
    db_session.add(user)
    db_session.commit()

    code1 = MFABackupCode(user_id=user.id, code_hash="hash1")
    code2 = MFABackupCode(user_id=user.id, code_hash="hash2")
    db_session.add_all([code1, code2])
    db_session.commit()

    assert len(user.backup_codes) == 2

    # Eliminar user y verificar cascade delete
    db_session.delete(user)
    db_session.commit()

    remaining_codes = db_session.query(MFABackupCode).filter(MFABackupCode.user_id == user.id).all()
    assert len(remaining_codes) == 0
