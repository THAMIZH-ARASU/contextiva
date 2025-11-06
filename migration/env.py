from __future__ import annotations

import os
from urllib.parse import quote_plus
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _build_sync_db_url_from_env() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "contextiva")
    user = quote_plus(os.getenv("POSTGRES_USER", "contextiva"))
    pwd = quote_plus(os.getenv("POSTGRES_PASSWORD", "changeme"))
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    url = _build_sync_db_url_from_env()
    config.set_main_option("sqlalchemy.url", url)
    context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Override URL from environment (.env) to avoid hardcoding credentials in alembic.ini
    url = _build_sync_db_url_from_env()
    config.set_main_option("sqlalchemy.url", url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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


