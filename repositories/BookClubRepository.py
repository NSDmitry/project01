from typing import List

from sqlalchemy.orm import Session

from DBmodels import DBUser, DBBookClub
from services.BookClub.Models import CreateBookClubRequestModel


class BookClubRepository:
    @classmethod
    def create_book_blub(cls, owner: DBUser, model: CreateBookClubRequestModel, db: Session) -> DBBookClub:
        new_book_club = DBBookClub(name=model.name, description=model.description, owner_id=owner.id, owner=owner, members=[owner])

        db.add(new_book_club)
        db.commit()
        db.refresh(new_book_club)

        return new_book_club

    @classmethod
    def get_owned_book_blubs(cls, owner: DBUser, db: Session) -> List[DBBookClub]:
        clubs = db.query(DBBookClub).filter(DBBookClub.owner_id == owner.id)

        return clubs