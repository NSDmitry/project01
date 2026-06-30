from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound
from app.db.models.db_discussion import DBDiscussion
from app.schemas.discussions_schema import DiscussionCreateRequestModel


class DiscussionRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_discussions(self, book_club_id: int) -> List[DBDiscussion]:
        result = await self.db.execute(select(DBDiscussion).where(DBDiscussion.club_id == book_club_id))

        return result.scalars().all()

    async def get_discussion(self, discussion_id: int) -> DBDiscussion:
        result = await self.db.execute(select(DBDiscussion).where(DBDiscussion.id == discussion_id))
        discussion = result.scalar_one_or_none()

        if not discussion:
            raise NotFound(errors=["Обсуждение с таким id не найдено"])

        return discussion

    async def create_discussion(self, author_id: int, model: DiscussionCreateRequestModel) -> DBDiscussion:
        new_discussion = DBDiscussion()
        new_discussion.club_id = model.club_id
        new_discussion.author_id = author_id
        new_discussion.title = model.title
        new_discussion.content = model.content

        self.db.add(new_discussion)
        await self.db.commit()
        await self.db.refresh(new_discussion)

        return new_discussion

    async def delete_discussion(self, discussion_id: int) -> DBDiscussion:
        result = await self.db.execute(select(DBDiscussion).where(DBDiscussion.id == discussion_id))
        discussion = result.scalar_one_or_none()
        if discussion:
            await self.db.delete(discussion)
            await self.db.commit()

        return discussion

    async def update_discussion(self, discussion: DBDiscussion, model: DiscussionCreateRequestModel) -> DBDiscussion:
        discussion.title = model.title
        discussion.content = model.content

        await self.db.commit()
        await self.db.refresh(discussion)

        return discussion
