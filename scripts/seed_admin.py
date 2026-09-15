import asyncio
import os
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash


async def seed_data():
    """Inicializa tablas y crea usuarios base para desarrollo y sustentación."""
    print("Creando tablas si no existen...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Usuario Administrador Institucional (Johan)
        sebas_email = "jsebastianposada@ucundinamarca.edu.co"
        sebas_user = db.query(User).filter(User.email == sebas_email).first()
        if not sebas_user:
            sebas_user = User(
                email=sebas_email,
                full_name="Johan Sebastián Posada Beltrán",
                hashed_password=get_password_hash("Admin123!"),
                role="admin",
                is_active=True,
                must_change_password=False,
            )
            db.add(sebas_user)
            db.commit()
            print(f"✅ Usuario creado: {sebas_email}")
        else:
            print(f"ℹ️ Usuario {sebas_email} ya existe.")

        # 2. Usuario Compañero (Juan Pablo)
        juan_email = "jpablofonseca@ucundinamarca.edu.co"
        juan_user = db.query(User).filter(User.email == juan_email).first()
        if not juan_user:
            juan_user = User(
                email=juan_email,
                full_name="Juan Pablo Fonseca Celis",
                hashed_password=get_password_hash("Admin123!"),
                role="admin",
                is_active=True,
                must_change_password=False,
            )
            db.add(juan_user)
            db.commit()
            print(f"✅ Usuario creado: {juan_email}")
        else:
            print(f"ℹ️ Usuario {juan_email} ya existe.")

        # 3. Usuario de Prueba Rápida (demo / testing)
        demo_email = "admin@honeymetrics.com"
        demo_user = db.query(User).filter(User.email == demo_email).first()
        if not demo_user:
            demo_user = User(
                email=demo_email,
                full_name="Administrador de Pruebas",
                hashed_password=get_password_hash("Admin123!"),
                role="admin",
                is_active=True,
                must_change_password=False,
            )
            db.add(demo_user)
            db.commit()
            print(f"✅ Usuario de prueba creado: {demo_email}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
