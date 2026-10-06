from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Role, User
from app.core.security import hash_password
from app.services.auth_service import authenticate_user
import pytest


@pytest.fixture
def db():
    # Arrange en fixtures
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def active_user(db):
    # Arrange en fixtures
    role = Role(name="admin", description="Administrador")

    user = User(
        email="correo@prueba.com",
        first_names="Usuario",
        last_names="Prueba",
        hashed_password=hash_password("Testing"),
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def test_correct_auth(db, active_user):
    # Act: llamada al servicio
    authenticated_user = authenticate_user(db, "correo@prueba.com", "Testing")

    assert authenticated_user is not None
    assert authenticated_user.id == active_user.id
    assert authenticated_user.email == "correo@prueba.com"


def test_rejects_incorrect_password(db, active_user):
    authenticated_user = authenticate_user(
        db,
        "correo@prueba.com",
        "Incorrecta123",
    )

    assert authenticated_user is None


def test_rejects_unknown_email(db, active_user):
    authenticated_user = authenticate_user(
        db,
        "inexistente@prueba.com",
        "Testing",
    )

    assert authenticated_user is None


def test_rejects_inactive_user(db, active_user):
    active_user.is_active = False
    db.commit()

    authenticated_user = authenticate_user(
        db,
        "correo@prueba.com",
        "Testing",
    )

    assert authenticated_user is None
