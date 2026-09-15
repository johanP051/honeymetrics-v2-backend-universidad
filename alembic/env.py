from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 1. Importar configuracion de la app y los modelos
from app.core.config import settings
from app.db.base import Base # Base es lo que usa Alembic para saber que modelos tiene la app para hacer la migraciones; en django esto estaba implicito en django.apps
import app.models #carga Role y User en Base.metadata


# Config de alembic leyendo alembic.ini, config es un objeto de configuracion
config = context.config

# Se toma objeto config y se hace: Inyeccion de la URL de la BDD mediante las variables de entorno
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configurar logs
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Conectar la metadata de los modelos para que autogenerate funcione, con metadata se le dice a alembic cuales son las tablas y como estan construidas
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Modo offline: genera raw SQL para ejecutar manualmente y generar las tablas (DB First)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: se conecta a la BD y aplica cambios automaticamente (Code First)"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
