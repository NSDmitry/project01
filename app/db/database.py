from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv
from app.settings import settings

load_dotenv()

Base = declarative_base()

# Синхронный движок - используется миграциями Alembic, standalone-скриптами и тестами.
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=True)

# Асинхронный движок - используется путём запроса (зависимости FastAPI).
async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
async_engine = create_async_engine(async_database_url, echo=False)
# expire_on_commit=False: после commit атрибуты не инвалидируются, иначе обращение
# к ним вне async-контекста запустило бы ленивый I/O и упало.
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
