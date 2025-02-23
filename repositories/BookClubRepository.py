from sqlalchemy.orm import Session

from DBmodels import DBUser, DBBookClub
from services.BookClub.Models import CreateBookClubRequestModel


class BookClubRepository:
    @classmethod
    def create_book_blub(cls, user: DBUser, model: CreateBookClubRequestModel, db: Session) -> DBBookClub:
        new_book_club = DBBookClub(name=model.name, description=model.description, owner_id=user.id)

        db.add(new_book_club)
        db.commit()
        db.refresh(new_book_club)

        return new_book_club