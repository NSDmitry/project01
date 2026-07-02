from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound
from app.db.models.db_comment import Comment
from app.schemas.comments_schema import CommentCreateRequest, CommentUpdateRequest


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
