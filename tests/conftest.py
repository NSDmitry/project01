import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.database import Base, get_db
from app.settings import settings
from fastapi.testclient import TestClient
from app.main import app

from tests.support.api import ApiClient

# Подключаемся к тестовой БД
engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Конфиг Alembic с абсолютными путями, чтобы не зависеть от cwd при запуске тестов
_BASE_DIR = Path(__file__).resolve().parents[1]
_alembic_cfg = Config(str(_BASE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(_BASE_DIR / "migrations"))
_alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

# migrations/env.py берёт URL из os.getenv("DATABASE_URL") и через load_dotenv()
# может подхватить дев-.env (5432). Прибиваем тестовый URL, чтобы миграции в тестах
# гарантированно шли в тестовую БД, а не в дев.
os.environ["DATABASE_URL"] = settings.database_url


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
def client(db):
    # Переопределим зависимость get_db на тестовую
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def api(client: TestClient) -> ApiClient:
    return ApiClient(client)

@pytest.fixture(autouse=True)
def clear_db(db):
    db.execute(text("SET session_replication_role = 'replica';"))

    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())

    db.execute(text("SET session_replication_role = 'origin';"))
    db.commit()
