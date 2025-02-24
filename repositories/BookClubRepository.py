from typing import List

from fastapi import HTTPException
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

    @classmethod
    def delete_book_club(cls, owner: DBUser, club_id: int, db: Session):
        club: DBBookClub = db.query(DBBookClub).filter(DBBookClub.id == club_id).first()

        if club is None:
            raise HTTPException(status_code=404, detail="Книжный клуб с таким id не найден")

        if club.owner_id != owner.id:
            raise HTTPException(status_code=401, detail="Пользователь не являеется владельцем книжного клуба")

        db.delete(club)
        db.commit()