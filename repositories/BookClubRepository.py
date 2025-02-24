from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from DBmodels import DBUser, DBBookClub
from database import get_db
from services.BookClub.Models import CreateBookClubRequestModel


class BookClubRepository:
    db: Session

    def __init__(self, db: Session = get_db()) -> None:
        self.db = get_db()

    def create_book_blub(self, owner: DBUser, model: CreateBookClubRequestModel) -> DBBookClub:
        new_book_club = DBBookClub(name=model.name, description=model.description, owner_id=owner.id, owner=owner, members=[owner])

        self.db.add(new_book_club)
        self.db.commit()
        self.db.refresh(new_book_club)

        return new_book_club

    def get_book_clubs(self) -> List[DBBookClub]:
        clubs: List[DBBookClub] = self.db.query(DBBookClub)

        return clubs

    def get_owned_book_blubs(self, owner: DBUser) -> List[DBBookClub]:
        clubs = self.db.query(DBBookClub).filter(DBBookClub.owner_id == owner.id)

        return clubs

    def delete_book_club(self, owner: DBUser, club_id: int):
        club: DBBookClub = self.db.query(DBBookClub).filter(DBBookClub.id == club_id).first()

        if club is None:
            raise HTTPException(status_code=404, detail="Книжный клуб с таким id не найден")

        if club.owner_id != owner.id:
            raise HTTPException(status_code=401, detail="Пользователь не являеется владельцем книжного клуба")

        self.db.delete(club)
        self.db.commit()