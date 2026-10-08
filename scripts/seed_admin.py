import asyncio
import os
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.role_model import Role
from app.models.user_model import User
from app.core.security import hash_password


async def seed_data():
    """Inicializa tablas y crea usuarios base para desarrollo y sustentación."""
    seed_password = os.getenv("SEED_ADMIN_PASSWORD")
    if not seed_password:
        raise RuntimeError("SEED_ADMIN_PASSWORD es obligatorio para ejecutar el seed.")

    print("Creando tablas si no existen...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is None:
            admin_role = Role(name="admin", description="Administrador del sistema")
            db.add(admin_role)
            db.flush()

        seed_users = (
            ("jsebastianposada@ucundinamarca.edu.co", "Johan Sebastián Posada Beltrán"),
            ("jpablofonseca@ucundinamarca.edu.co", "Juan Pablo Fonseca Celis"),
            ("admin@honeymetrics.com", "Administrador de Pruebas"),
        )
        for email, full_name in seed_users:
            first_names, _, last_names = full_name.partition(" ")
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                user = User(
                    email=email,
                    first_names=first_names,
                    last_names=last_names or first_names,
                    hashed_password=hash_password(seed_password),
                    role_id=admin_role.id,
                    is_active=True,
                    must_change_password=False,
                )
                db.add(user)
                print(f"Usuario creado: {email}")
            else:
                print(f"Usuario {email} ya existe.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
