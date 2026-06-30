from typing import List

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound, Forbidden, Conflict
from app.db.models.db_user import DBUser
from app.db.models.db_book_club import DBBookClub
from app.schemas.book_club_schema import CreateBookClubRequestModel


class BookClubRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_book_club(self, owner: DBUser, model: CreateBookClubRequestModel) -> DBBookClub:
        new_book_club = DBBookClub()
        new_book_club.name = model.name
        new_book_club.description = model.description
        new_book_club.owner_id = owner.id
        new_book_club.members_ids = [owner.id]

        self.db.add(new_book_club)
        await self.db.commit()
        await self.db.refresh(new_book_club)

        return new_book_club

    async def get_book_clubs(self) -> List[DBBookClub]:
        result = await self.db.execute(select(DBBookClub))

        return result.scalars().all()

    async def get_owned_book_clubs(self, owner: DBUser) -> List[DBBookClub]:
        result = await self.db.execute(select(DBBookClub).where(DBBookClub.owner_id == owner.id))

        return result.scalars().all()

    async def get_book_club(self, club_id: int) -> DBBookClub:
        result = await self.db.execute(select(DBBookClub).where(DBBookClub.id == club_id))
        club = result.scalar_one_or_none()

        if club is None:
            raise NotFound("Книжный клуб с таким id не найден")

        return club

    async def delete_book_club(self, owner: DBUser, club_id: int):
        result = await self.db.execute(select(DBBookClub).where(DBBookClub.id == club_id))
        club = result.scalar_one_or_none()

        if club is None:
            raise NotFound("Книжный клуб с таким id не найден")

        if club.owner_id != owner.id:
            raise Forbidden("Пользователь не является владельцем книжного клуба")

        await self.db.delete(club)
        await self.db.commit()

    async def join_book_club(self, user: DBUser, club_id: int) -> DBBookClub:
        club: DBBookClub = await self.get_book_club(club_id=club_id)

        if user.id not in club.members_ids:
            club.members_ids.append(user.id)
            flag_modified(club, "members_ids")
            await self.db.commit()
            await self.db.refresh(club)
        else:
            raise Conflict(errors=["Пользователь уже является участником клуба, повторное добавление не требуется"])

        return club

    async def remove_member(self, user: DBUser, club_id: int) -> DBBookClub:
        club: DBBookClub = await self.get_book_club(club_id=club_id)

        if user.id not in club.members_ids:
            raise Conflict(errors=["Пользователь не состоит в клубе"])

        club.members_ids.remove(user.id)
        flag_modified(club, "members_ids")

        await self.db.commit()
        await self.db.refresh(club)

        return club
