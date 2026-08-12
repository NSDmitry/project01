from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from service.settings import settings

Base = declarative_base()

async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
async_engine = create_async_engine(async_database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Граница транзакции - запрос: фиксируем один раз здесь, ошибка откатывает всё.
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
