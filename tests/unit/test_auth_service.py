from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Role, User
from app.core.security import hash_password
from app.services.auth_service import authenticate_user

def test_correct_auth():
    engine = create_engine("sqlite:///:memory:") #Conexion a sqlite
    Base.metadata.create_all(engine) #Crea las tablas en la base temporal

    with Session(engine) as db:
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

        authenticated_user = authenticate_user(
            db,
            "correo@prueba.com",
            "Testing"
        )

        assert authenticated_user is not None
        assert authenticated_user.email == "correo@prueba.com"

