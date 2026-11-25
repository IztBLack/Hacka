"""Entorno de Alembic: URL desde app.config y metadatos desde app.modelos."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.modelos  # noqa: F401  (registra todas las tablas en Base.metadata)
from app.config import settings
from app.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    """Permite sobrescribir la URL (pruebas); si no, usa la de la aplicación."""
    return config.get_main_option("sqlalchemy.url") or settings.url_base_datos


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuracion = config.get_section(config.config_ini_section, {})
    configuracion["sqlalchemy.url"] = _url()
    conectable = engine_from_config(
        configuracion, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with conectable.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
