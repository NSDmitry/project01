from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound
from app.discussions.models import Thread, Comment
from app.discussions.schemas import ThreadCreateRequest, CommentCreateRequest, CommentUpdateRequest


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


class CommentRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_comments(self, thread_id: int, limit: int, offset: int) -> Tuple[List[Comment], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(Comment).where(Comment.thread_id == thread_id)
        )
        result = await self.db.execute(
            select(Comment)
            .where(Comment.thread_id == thread_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    async def get_comment(self, comment_id: int) -> Comment:
        result = await self.db.execute(select(Comment).where(Comment.id == comment_id))
        comment = result.scalar_one_or_none()

        if not comment:
            raise NotFound(errors=["Комментарий с таким id не найден"])

        return comment

    async def create_comment(self, thread_id: int, author_id: int, model: CommentCreateRequest) -> Comment:
        new_comment = Comment()
        new_comment.thread_id = thread_id
        new_comment.author_id = author_id
        new_comment.content = model.content

        self.db.add(new_comment)
        await self.db.flush()

        return await self.get_comment(new_comment.id)

    async def delete_comment(self, comment_id: int) -> Comment:
        result = await self.db.execute(select(Comment).where(Comment.id == comment_id))
        comment = result.scalar_one_or_none()
        if comment:
            await self.db.delete(comment)
            await self.db.flush()

        return comment

    async def update_comment(self, comment: Comment, model: CommentUpdateRequest) -> Comment:
        comment.content = model.content

        await self.db.flush()

        return await self.get_comment(comment.id)
