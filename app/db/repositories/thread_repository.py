from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound
from app.db.models.db_thread import DBThread
from app.schemas.threads_schema import ThreadCreateRequestModel


class ThreadRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_threads(self, club_id: int, limit: int, offset: int) -> Tuple[List[DBThread], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(DBThread).where(DBThread.club_id == club_id)
        )
        result = await self.db.execute(
            select(DBThread)
            .where(DBThread.club_id == club_id)
            .order_by(DBThread.created_at.desc(), DBThread.id.desc())
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    async def get_thread(self, thread_id: int) -> DBThread:
        result = await self.db.execute(select(DBThread).where(DBThread.id == thread_id))
        thread = result.scalar_one_or_none()

        if not thread:
            raise NotFound(errors=["Тред с таким id не найден"])

        return thread

    async def create_thread(self, author_id: int, model: ThreadCreateRequestModel) -> DBThread:
        new_thread = DBThread()
        new_thread.club_id = model.club_id
        new_thread.author_id = author_id
        new_thread.title = model.title
        new_thread.content = model.content

        self.db.add(new_thread)
        await self.db.flush()

        return await self.get_thread(new_thread.id)

    async def delete_thread(self, thread_id: int) -> DBThread:
        result = await self.db.execute(select(DBThread).where(DBThread.id == thread_id))
        thread = result.scalar_one_or_none()
        if thread:
            await self.db.delete(thread)
            await self.db.flush()

        return thread

    async def update_thread(self, thread: DBThread, model: ThreadCreateRequestModel) -> DBThread:
        thread.title = model.title
        thread.content = model.content

        await self.db.flush()

        return await self.get_thread(thread.id)
