from getpass import getpass

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Role, User


def create_admin() -> None:
    db = SessionLocal()

    try:
        print("Conectado a la base de datos")

        email = input("Email del administrador: ").strip()

        if not email:
            raise ValueError("El email no puede estar vacio")

        existing_user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if existing_user is not None:
            print("Ya existe un usuario con ese email")
            return

        password = getpass("Contrasena del administrador: ")
        password_confirmation = getpass("Repita la contrasena: ")

        if not password:
            raise ValueError("La contrasena no puede estar vacia")

        if password != password_confirmation:
            raise ValueError("Las contrasenas no coinciden")

        role = (
            db.query(Role)
            .filter(Role.name == "admin")
            .first()
        )

        if role is None:
            role = Role(
                name="admin",
                description="Administrador",
            )
            db.add(role)
            db.flush()

        admin = User(
            email=email,
            first_names="Administrador",
            last_names="Sistema",
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
            must_change_password=False,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"Administrador creado correctamente con id {admin.id}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()

# input email
#     -> comprobar que no exista
#     -> pedir contraseña sin mostrarla
#     -> generar hash
#     -> buscar o crear rol admin
#     -> crear User
#     -> db.add()
#     -> db.commit()
#     -> cerrar sesión

# db.add(admin) prepara el usuario para guardarlo.
# db.commit() confirma la transacción en PostgreSQL.
# db.refresh(admin) actualiza el objeto con su id generado.
# db.rollback() deshace los cambios si ocurre un error.
# finally cierra la conexión siempre.
# hash_password(password) evita guardar la contraseña en texto plano.
# Al usar SQLAlchemy, created_at y updated_at deberían generarse mediante los valores por defecto del modelo.

