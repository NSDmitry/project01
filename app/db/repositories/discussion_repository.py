from typing import List

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.db_discussion import DBDiscussion
from app.schemas.discussions_schema import DiscussionCreateRequestModel


class DiscussionRepository:
    db: Session

    def __init__(self, db: Session = get_db()) -> None:
        self.db = db

    def get_discussions(self, book_club_id: int) -> List[DBDiscussion]:
        discussions = self.db.query(DBDiscussion).filter(DBDiscussion.club_id == book_club_id).all()

        return discussions

    def create_discussion(self, author_id: int, model: DiscussionCreateRequestModel) -> DBDiscussion:
        new_discussion = DBDiscussion(
            club_id = model.club_id,
            author_id = author_id,
            title = model.title,
            content = model.content,
        )

        self.db.add(new_discussion)
        self.db.commit()
        self.db.refresh(new_discussion)

        return new_discussion