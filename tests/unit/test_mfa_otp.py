"""TDD RED - 2FA-OTP (PB-HM-07.1, port de guia).

Contrato:
- POST /auth/mfa/setup (autenticado) -> 200 con qr + secret.
- POST /auth/mfa/verify con codigo TOTP valido -> 200 y activa 2FA.
- POST /auth/mfa/verify con codigo invalido -> 400.
- Login con 2FA activo -> 200 con mfa_required=True + mfa_token.
- POST /auth/mfa/verify-login con OTP correcto -> JWT final.
- POST /auth/mfa/verify-login con OTP incorrecto -> 401.
"""

import pyotp
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Role, User
from app.core.security import hash_password

from fastapi.testclient import TestClient


@pytest.fixture
def test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def test_database(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_engine, test_database):
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def active_user(db_session):
    role = Role(name="admin", description="Administrador")
    user = User(
        email="mfa@ucundinamarca.edu.co",
        first_names="Mfa",
        last_names="Prueba",
        hashed_password=hash_password("Testing123"),
        role=role,
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _login(client, email="mfa@ucundinamarca.edu.co", password="Testing123"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_mfa_setup_returns_qr_and_secret(client, active_user):
    token = _login(client)["access_token"]
    resp = client.post("/api/v1/auth/mfa/setup", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "qr" in data
    assert "secret" in data


def test_mfa_verify_invalid_code_returns_400(client, active_user):
    token = _login(client)["access_token"]
    client.post("/api/v1/auth/mfa/setup", headers=_auth(token))
    resp = client.post("/api/v1/auth/mfa/verify", headers=_auth(token), json={"code": "000000"})
    assert resp.status_code == 400


def test_mfa_verify_valid_code_enables(client, active_user, db_session):
    token = _login(client)["access_token"]
    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(token)).json()
    code = pyotp.TOTP(setup["secret"]).now()
    resp = client.post("/api/v1/auth/mfa/verify", headers=_auth(token), json={"code": code})
    assert resp.status_code == 200
    db_session.refresh(active_user)
    assert active_user.is_mfa_enabled is True


def test_login_with_mfa_returns_mfa_required(client, active_user, db_session):
    token = _login(client)["access_token"]
    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(token)).json()
    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/api/v1/auth/mfa/verify", headers=_auth(token), json={"code": code})
    db_session.refresh(active_user)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@ucundinamarca.edu.co", "password": "Testing123"},
    )
    assert login.status_code == 200
    data = login.json()
    assert data["mfa_required"] is True
    assert "mfa_token" in data
    assert "access_token" not in data or not data.get("access_token")


def test_mfa_verify_login_wrong_code_returns_401(client, active_user, db_session):
    token = _login(client)["access_token"]
    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(token)).json()
    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/api/v1/auth/mfa/verify", headers=_auth(token), json={"code": code})
    db_session.refresh(active_user)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@ucundinamarca.edu.co", "password": "Testing123"},
    )
    mfa_token = login.json()["mfa_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": "000000"},
    )
    assert resp.status_code == 401


def test_mfa_verify_login_correct_code_returns_jwt(client, active_user, db_session):
    token = _login(client)["access_token"]
    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(token)).json()
    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/api/v1/auth/mfa/verify", headers=_auth(token), json={"code": code})
    db_session.refresh(active_user)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@ucundinamarca.edu.co", "password": "Testing123"},
    )
    mfa_token = login.json()["mfa_token"]
    final_code = pyotp.TOTP(setup["secret"]).now()
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": final_code},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_mfa_disable_stops_requiring_otp(client, active_user, db_session):
    token = _login(client)["access_token"]
    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(token)).json()
    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/api/v1/auth/mfa/verify", headers=_auth(token), json={"code": code})
    db_session.refresh(active_user)
    assert active_user.is_mfa_enabled is True

    disable = client.post("/api/v1/auth/mfa/disable", headers=_auth(token))
    assert disable.status_code == 200
    db_session.refresh(active_user)
    assert active_user.is_mfa_enabled is False
    assert active_user.totp_secret is None

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@ucundinamarca.edu.co", "password": "Testing123"},
    )
    assert login.status_code == 200
    assert login.json()["mfa_required"] is False
    assert "access_token" in login.json()


def test_mfa_verify_login_rejects_normal_jwt(client, active_user, db_session):
    token = _login(client)["access_token"]
    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(token)).json()
    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/api/v1/auth/mfa/verify", headers=_auth(token), json={"code": code})
    db_session.refresh(active_user)

    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": token, "code": "123456"},
    )
    assert resp.status_code == 401


def test_login_without_mfa_still_returns_token(client, active_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@ucundinamarca.edu.co", "password": "Testing123"},
    )
    assert login.status_code == 200
    assert login.json()["mfa_required"] is False
    assert "access_token" in login.json()
