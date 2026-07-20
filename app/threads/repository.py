from typing import Dict, List, Set, Tuple

from sqlalchemy import select, func, delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound
from app.threads.models import Thread, Comment, CommentLike
from app.threads.schemas import ThreadCreateRequest, CommentCreateRequest, CommentUpdateRequest


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

    async def create_thread(self, author_id: int, model: ThreadCreateRequest, book_id: int = None) -> Thread:
        new_thread = Thread()
        new_thread.club_id = model.club_id
        new_thread.author_id = author_id
        new_thread.book_id = book_id
        new_thread.title = model.title
        new_thread.content = model.content

        self.db.add(new_thread)
        await self.db.flush()

        return await self.get_thread(new_thread.id)

    async def get_threads_counts(self, club_ids: List[int]) -> Dict[int, int]:
        if not club_ids:
            return {}

        result = await self.db.execute(
            select(Thread.club_id, func.count())
            .where(Thread.club_id.in_(club_ids))
            .group_by(Thread.club_id)
        )

        return dict(result.all())

    async def handle_clubs_deleted(self, club_ids: List[int]) -> None:
        # FK threads.club_id на book_clubs больше нет - CASCADE при удалении
        # клуба выполняем явно. Комменты и лайки чистят каскады БД по
        # thread_id/comment_id.
        if not club_ids:
            return

        await self.db.execute(delete(Thread).where(Thread.club_id.in_(club_ids)))
        await self.db.flush()

    async def handle_user_deleted(self, user_id: int, delete_threads: bool, delete_comments: bool) -> None:
        # FK на users больше нет - SET NULL/CASCADE, которые раньше делала БД
        # при удалении пользователя, выполняем явно. Вложенное (комменты, лайки)
        # чистят каскады БД по thread_id/comment_id.
        if delete_threads:
            await self.db.execute(delete(Thread).where(Thread.author_id == user_id))
        else:
            await self.db.execute(
                update(Thread).values(author_id=None).where(Thread.author_id == user_id)
            )
        if delete_comments:
            await self.db.execute(delete(Comment).where(Comment.author_id == user_id))
        else:
            await self.db.execute(
                update(Comment).values(author_id=None).where(Comment.author_id == user_id)
            )
        await self.db.execute(delete(CommentLike).where(CommentLike.user_id == user_id))
        await self.db.flush()

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

    async def add_like(self, comment_id: int, user_id: int) -> None:
        # ON CONFLICT DO NOTHING: конкурентные лайки одного пользователя не падают об уникальный ключ
        await self.db.execute(
            pg_insert(CommentLike)
            .values(comment_id=comment_id, user_id=user_id)
            .on_conflict_do_nothing(constraint="uq_comment_likes_comment_id_user_id")
        )

    async def remove_like(self, comment_id: int, user_id: int) -> None:
        result = await self.db.execute(
            select(CommentLike)
            .where(CommentLike.comment_id == comment_id, CommentLike.user_id == user_id)
        )
        like = result.scalar_one_or_none()
        if like:
            await self.db.delete(like)
            await self.db.flush()

    async def get_likes_counts(self, comment_ids: List[int]) -> Dict[int, int]:
        if not comment_ids:
            return {}

        result = await self.db.execute(
            select(CommentLike.comment_id, func.count())
            .where(CommentLike.comment_id.in_(comment_ids))
            .group_by(CommentLike.comment_id)
        )

        return dict(result.all())

    async def get_liked_comment_ids(self, comment_ids: List[int], user_id: int) -> Set[int]:
        if not comment_ids:
            return set()

        result = await self.db.execute(
            select(CommentLike.comment_id)
            .where(CommentLike.comment_id.in_(comment_ids), CommentLike.user_id == user_id)
        )

        return set(result.scalars().all())
