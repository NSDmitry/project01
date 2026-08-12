from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from service.database import Base, get_db
from service.main import app
from service.settings import settings

# У сервиса своя БД (в проде тоже): тестовая создаётся на том же Postgres,
# что и тестовая БД монолита, но отдельным каталогом - иначе столкнёмся
# по alembic_version с миграциями монолита.
_url = make_url(settings.database_url)
_admin_engine = create_engine(
    _url.set(database="postgres").render_as_string(hide_password=False),
    isolation_level="AUTOCOMMIT",
)
with _admin_engine.connect() as _conn:
    if not _conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": _url.database}
    ).scalar():
        _conn.execute(text(f'CREATE DATABASE "{_url.database}"'))
_admin_engine.dispose()

# Синхронный движок - схема (Alembic), очистка таблиц и прямые проверки в тестах.
engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Асинхронный движок - путь запроса (через override get_db). NullPool: каждое
# соединение свежее и закрывается со своей сессией, иначе asyncpg переиспользует
# соединение из пула в другом event loop и падает с "attached to a different loop".
async_test_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
async_engine = create_async_engine(async_test_url, poolclass=NullPool)
AsyncTestingSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


async def override_get_db():
    # Зеркалит prod-границу транзакции (commit на успехе).
    async with AsyncTestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Конфиг Alembic с абсолютными путями, чтобы не зависеть от cwd при запуске тестов
_BASE_DIR = Path(__file__).resolve().parents[1]
_alembic_cfg = Config(str(_BASE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(_BASE_DIR / "migrations"))


def _reset_schema():
    # Полностью чистим схему, включая alembic_version, иначе upgrade станет no-op
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))


# Перед сессией тестов строим схему ровно так же, как в проде - через миграции
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    _reset_schema()
    command.upgrade(_alembic_cfg, "head")
    yield
    _reset_schema()


@pytest.fixture()
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
async def async_db():
    async with AsyncTestingSessionLocal() as session:
        yield session


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_db(db):
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
