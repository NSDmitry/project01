import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# 👇 Добавляем путь к проекту, чтобы видеть твои модули
sys.path.append(str(Path(__file__).resolve().parents[1]))

# 👇 Загружаем переменные из .env
load_dotenv()
database_url = os.getenv("DATABASE_URL")

# ⬇️ Импортируй здесь Base из своего проекта
from app.db.database import Base # убедись, что путь корректный
from app.db import models

# Alembic config
config = context.config

# ⬇️ Перезаписываем URL из .env
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Логирование
if config.config_file_name:
    fileConfig(config.config_file_name)

# Метадата моделей (для автогенерации)
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
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