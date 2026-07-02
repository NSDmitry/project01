from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound
from app.db.models.db_thread import Thread
from app.schemas.threads_schema import ThreadCreateRequest


class ThreadRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_threads(self, club_id: int, limit: int, offset: int) -> Tuple[List[Thread], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(Thread).where(Thread.club_id == club_id)
        )
        result = await self.db.execute(
            select(Thread)
            .where(Thread.club_id == club_id)
            .order_by(Thread.created_at.desc(), Thread.id.desc())
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    async def get_thread(self, thread_id: int) -> Thread:
        result = await self.db.execute(select(Thread).where(Thread.id == thread_id))
        thread = result.scalar_one_or_none()

        if not thread:
            raise NotFound(errors=["Тред с таким id не найден"])

        return thread

    async def create_thread(self, author_id: int, model: ThreadCreateRequest) -> Thread:
        new_thread = Thread()
        new_thread.club_id = model.club_id
        new_thread.author_id = author_id
        new_thread.title = model.title
        new_thread.content = model.content

        self.db.add(new_thread)
        await self.db.flush()

        return await self.get_thread(new_thread.id)

    async def delete_thread(self, thread_id: int) -> Thread:
        result = await self.db.execute(select(Thread).where(Thread.id == thread_id))
        thread = result.scalar_one_or_none()
        if thread:
            await self.db.delete(thread)
            await self.db.flush()

        return thread

    async def update_thread(self, thread: Thread, model: ThreadCreateRequest) -> Thread:
        thread.title = model.title
        thread.content = model.content

        await self.db.flush()

        return await self.get_thread(thread.id)
