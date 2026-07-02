from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound
from app.db.models.db_comment import DBComment
from app.schemas.comments_schema import CommentCreateRequestModel, CommentUpdateRequestModel


class CommentRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_comments(self, thread_id: int, limit: int, offset: int) -> Tuple[List[DBComment], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(DBComment).where(DBComment.thread_id == thread_id)
        )
        result = await self.db.execute(
            select(DBComment)
            .where(DBComment.thread_id == thread_id)
            .order_by(DBComment.created_at.asc(), DBComment.id.asc())
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    async def get_comment(self, comment_id: int) -> DBComment:
        result = await self.db.execute(select(DBComment).where(DBComment.id == comment_id))
        comment = result.scalar_one_or_none()

        if not comment:
            raise NotFound(errors=["Комментарий с таким id не найден"])

        return comment

    async def create_comment(self, thread_id: int, author_id: int, model: CommentCreateRequestModel) -> DBComment:
        new_comment = DBComment()
        new_comment.thread_id = thread_id
        new_comment.author_id = author_id
        new_comment.content = model.content

        self.db.add(new_comment)
        await self.db.flush()

        return await self.get_comment(new_comment.id)

    async def delete_comment(self, comment_id: int) -> DBComment:
        result = await self.db.execute(select(DBComment).where(DBComment.id == comment_id))
        comment = result.scalar_one_or_none()
        if comment:
            await self.db.delete(comment)
            await self.db.flush()

        return comment

    async def update_comment(self, comment: DBComment, model: CommentUpdateRequestModel) -> DBComment:
        comment.content = model.content

        await self.db.flush()

        return await self.get_comment(comment.id)
