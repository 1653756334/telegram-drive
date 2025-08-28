from __future__ import annotations

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from alembic import context
import os
import sys

# Add backend path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config.database import Base  # noqa: E402
from app.config import get_settings  # noqa: E402
import app.infrastructure.database.models  # noqa: F401,E402  # ensure models are imported

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()

# Derive a sync URL for Alembic if app uses asyncpg
db_url = settings.database_url
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "+psycopg2")

# overwrite sqlalchemy.url with derived sync url
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

