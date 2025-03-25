from typing import List

from fastapi import HTTPException
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session

from DBmodels import DBUser, DBBookClub
from database import get_db
from services.BookClub.Models import CreateBookClubRequestModel


class BookClubRepository:
    db: Session

    def __init__(self, db: Session = get_db()) -> None:
        self.db = get_db()

    def create_book_blub(self, owner: DBUser, model: CreateBookClubRequestModel) -> DBBookClub:
        new_book_club = DBBookClub(name=model.name, description=model.description, owner_id=owner.id, members_ids=[owner.id])

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

    def get_book_club(self, club_id: int) -> DBBookClub:
        club = self.db.query(DBBookClub).filter(DBBookClub.id == club_id).first()

        if club is None:
            raise HTTPException(status_code=404, detail="Книжный клуб с таким id не найден")

        return club

    def delete_book_club(self, owner: DBUser, club_id: int):
        club: DBBookClub = self.db.query(DBBookClub).filter(DBBookClub.id == club_id).first()

        if club is None:
            raise HTTPException(status_code=404, detail="Книжный клуб с таким id не найден")

        if club.owner_id != owner.id:
            raise HTTPException(status_code=403, detail="Пользователь не является владельцем книжного клуба")

        self.db.delete(club)
        self.db.commit()

    def join_book_club(self, user: DBUser, club_id: int) -> DBBookClub:
        club: DBBookClub = self.get_book_club(club_id=club_id)

        if user.id not in club.members_ids:
            club.members_ids.append(user.id)
            flag_modified(club, "members_ids")
            self.db.commit()
            self.db.refresh(club)
        else:
            raise HTTPException(status_code=500, detail="Пользователь уже учатсник клуба")

        return club

    def remove_member(self, user: DBUser, club_id: int) -> DBBookClub:
        club: DBBookClub = self.get_book_club(club_id=club_id)

        if user.id not in club.members_ids:
            raise HTTPException(status_code=404, detail="Пользователь не участник клуба")

        club.members_ids.remove(user.id)
        flag_modified(club, "members_ids")

        self.db.commit()
        self.db.refresh(club)

        return club
