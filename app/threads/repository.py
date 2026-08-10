from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import select, func, delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound
from app.threads.models import Thread, Comment, CommentLike
from app.threads.schemas import (
    ThreadCreateRequest,
    ThreadUpdateRequest,
    CommentCreateRequest,
    CommentUpdateRequest,
)


class ThreadRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # Общее число тредов не считаем: его держит BookClub.threads_count, а клуб
    # сервис к этому моменту уже загрузил. Исключение - выборка по этапу захода,
    # для неё есть count_threads.
    async def get_threads(
        self, club_id: int, limit: int, offset: int, reading_stage_id: int | None = None
    ) -> List[Thread]:
        result = await self.db.execute(
            select(Thread)
            .where(*self._thread_filters(club_id, reading_stage_id))
            .order_by(Thread.created_at.desc(), Thread.id.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all())

    @staticmethod
    def _thread_filters(club_id: int, reading_stage_id: int | None) -> List[Any]:
        filters: List[Any] = [Thread.club_id == club_id]
        if reading_stage_id is not None:
            filters.append(Thread.reading_stage_id == reading_stage_id)

        return filters

    async def count_threads(self, club_id: int, reading_stage_id: int) -> int:
        total = await self.db.scalar(
            select(func.count())
            .select_from(Thread)
            .where(*self._thread_filters(club_id, reading_stage_id))
        )

        return total or 0

    async def get_thread(self, thread_id: int) -> Thread:
        thread = await self.db.get(Thread, thread_id)

        if thread is None:
            raise NotFound(errors=["Тред с таким id не найден"])

        return thread

    async def create_thread(self, author_id: int, model: ThreadCreateRequest, book_id: int | None = None) -> Thread:
        new_thread = Thread()
        new_thread.club_id = model.club_id
        new_thread.author_id = author_id
        new_thread.book_id = book_id
        new_thread.reading_stage_id = model.reading_stage_id
        new_thread.title = model.title
        new_thread.content = model.content

        self.db.add(new_thread)
        await self.db.flush()

        return await self.get_thread(new_thread.id)

    async def handle_clubs_deleted(self, club_ids: List[int]) -> None:
        # FK threads.club_id на book_clubs больше нет - CASCADE при удалении
        # клуба выполняем явно. Комменты и лайки чистят каскады БД по
        # thread_id/comment_id.
        if not club_ids:
            return

        await self.db.execute(delete(Thread).where(Thread.club_id.in_(club_ids)))
        await self.db.flush()

    async def handle_user_deleted(self, user_id: int, delete_threads: bool, delete_comments: bool) -> Dict[int, int]:
        # FK на users больше нет - SET NULL/CASCADE, которые раньше делала БД
        # при удалении пользователя, выполняем явно. Вложенное (комменты, лайки)
        # чистят каскады БД по thread_id/comment_id.
        # Возвращаем {club_id: сколько тредов автора удалено} - домену клубов,
        # чтобы он уменьшил свои счётчики тредов.
        threads_removed_by_club: Dict[int, int] = {}
        if delete_threads:
            result = await self.db.execute(
                select(Thread.club_id, func.count())
                .where(Thread.author_id == user_id)
                .group_by(Thread.club_id)
            )
            threads_removed_by_club = dict(result.tuples().all())
            await self.db.execute(delete(Thread).where(Thread.author_id == user_id))
        else:
            await self.db.execute(
                update(Thread).values(author_id=None).where(Thread.author_id == user_id)
            )
        if delete_comments:
            # Счётчик правим до удаления: после DELETE считать уже нечего.
            # Вычитаем ровно столько, сколько уходит из каждого треда.
            removed_by_thread = (
                select(Comment.thread_id, func.count().label("cnt"))
                .where(Comment.author_id == user_id)
                .group_by(Comment.thread_id)
                .subquery()
            )
            await self.db.execute(
                update(Thread)
                .where(Thread.id == removed_by_thread.c.thread_id)
                .values(comments_count=func.greatest(Thread.comments_count - removed_by_thread.c.cnt, 0))
                .execution_options(synchronize_session=False)
            )
            await self.db.execute(delete(Comment).where(Comment.author_id == user_id))
        else:
            await self.db.execute(
                update(Comment).values(author_id=None).where(Comment.author_id == user_id)
            )
        await self.db.execute(delete(CommentLike).where(CommentLike.user_id == user_id))
        await self.db.flush()

        return threads_removed_by_club

    async def delete_thread(self, thread_id: int) -> Thread | None:
        thread = await self.db.get(Thread, thread_id)

        if thread:
            await self.db.delete(thread)
            await self.db.flush()

        return thread

    async def update_thread(self, thread: Thread, model: ThreadUpdateRequest) -> Thread:
        thread.title = model.title
        thread.content = model.content

        # refresh, а не повторный get: после UPDATE поле updated_at (onupdate=now())
        # помечено просроченным, а get() отдаёт объект из identity map как есть.
        await self.db.flush()
        await self.db.refresh(thread)

        return thread


class CommentRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # Общее число комментариев не считаем: его держит Thread.comments_count,
    # а тред сервис к этому моменту уже загрузил.
    async def get_comments(self, thread_id: int, limit: int, offset: int) -> List[Comment]:
        result = await self.db.execute(
            select(Comment)
            .where(Comment.thread_id == thread_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all())

    async def _change_comments_count(self, thread_id: int, delta: int) -> None:
        # Инкремент на стороне БД - параллельные комментарии в один тред иначе
        # затирали бы приращения друг друга.
        await self.db.execute(
            update(Thread)
            .where(Thread.id == thread_id)
            .values(comments_count=func.greatest(Thread.comments_count + delta, 0))
            .execution_options(synchronize_session="fetch")
        )

    async def get_comment(self, comment_id: int) -> Comment:
        comment = await self.db.get(Comment, comment_id)

        if comment is None:
            raise NotFound(errors=["Комментарий с таким id не найден"])

        return comment

    async def create_comment(self, thread_id: int, author_id: int, model: CommentCreateRequest) -> Comment:
        new_comment = Comment()
        new_comment.thread_id = thread_id
        new_comment.author_id = author_id
        new_comment.content = model.content

        self.db.add(new_comment)
        await self.db.flush()
        await self._change_comments_count(thread_id, +1)

        return await self.get_comment(new_comment.id)

    async def delete_comment(self, comment_id: int) -> Comment | None:
        comment = await self.db.get(Comment, comment_id)

        if comment:
            thread_id = comment.thread_id
            await self.db.delete(comment)
            await self.db.flush()
            await self._change_comments_count(thread_id, -1)

        return comment

    async def update_comment(self, comment: Comment, model: CommentUpdateRequest) -> Comment:
        comment.content = model.content

        await self.db.flush()
        await self.db.refresh(comment)

        return comment

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

    async def get_likers(self, comment_id: int, limit: int, offset: int) -> Tuple[List[int], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(CommentLike).where(CommentLike.comment_id == comment_id)
        )
        result = await self.db.execute(
            select(CommentLike.user_id)
            .where(CommentLike.comment_id == comment_id)
            .order_by(CommentLike.created_at.desc(), CommentLike.id.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all()), total or 0

    async def get_likes_counts(self, comment_ids: List[int]) -> Dict[int, int]:
        if not comment_ids:
            return {}

        result = await self.db.execute(
            select(CommentLike.comment_id, func.count())
            .where(CommentLike.comment_id.in_(comment_ids))
            .group_by(CommentLike.comment_id)
        )

        return dict(result.tuples().all())

    async def get_liked_comment_ids(self, comment_ids: List[int], user_id: int) -> Set[int]:
        if not comment_ids:
            return set()

        result = await self.db.execute(
            select(CommentLike.comment_id)
            .where(CommentLike.comment_id.in_(comment_ids), CommentLike.user_id == user_id)
        )

        return set(result.scalars().all())
