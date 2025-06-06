import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.database import Base, get_db
from app.settings import settings
from fastapi.testclient import TestClient
from app.main import app

# Подключаемся к тестовой БД
engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Перед каждым тестом пересоздаем таблицы
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

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

@pytest.fixture(autouse=True)
def clear_db(db):
    db.execute(text("SET session_replication_role = 'replica';"))

    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())

    db.execute(text("SET session_replication_role = 'origin';"))
    db.commit()