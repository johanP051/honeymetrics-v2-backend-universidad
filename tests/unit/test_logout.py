"""TDD RED - Cierre de sesion server-side (academico, port de guia).

Contrato: POST /auth/logout revoca el JWT (denylist jti),
el token reutilizado responde 401.
"""

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
        email="logout@ucundinamarca.edu.co",
        first_names="Logout",
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


def _token(client, email):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Testing123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_logout_returns_200(client, active_user):
    token = _token(client, active_user.email)
    resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_revoked_token_is_rejected(client, active_user):
    token = _token(client, active_user.email)
    ok = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200
    client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    denied = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 401


def test_logout_without_token_returns_401(client):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401
