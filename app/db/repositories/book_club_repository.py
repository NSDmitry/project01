from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound, Forbidden, Conflict
from app.db.models.db_user import DBUser
from app.db.models.db_book_club import DBBookClub
from app.db.models.db_club_member import DBClubMember
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

        self.db.add(new_book_club)

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflict(
                message="Клуб с таким названием уже существует",
                errors=["field: name, message: Это имя уже используется"],
            )

        self.db.add(DBClubMember(club_id=new_book_club.id, user_id=owner.id))
        await self.db.commit()

        return await self.get_book_club(club_id=new_book_club.id)

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

    async def is_member(self, club_id: int, user_id: int) -> bool:
        member = await self.db.get(DBClubMember, {"club_id": club_id, "user_id": user_id})

        return member is not None

    async def get_members(self, club_id: int, limit: int, offset: int) -> Tuple[List[DBUser], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(DBClubMember).where(DBClubMember.club_id == club_id)
        )
        result = await self.db.execute(
            select(DBUser)
            .join(DBClubMember, DBClubMember.user_id == DBUser.id)
            .where(DBClubMember.club_id == club_id)
            .order_by(DBUser.id)
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    async def delete_book_club(self, owner: DBUser, club_id: int):
        club = await self.get_book_club(club_id=club_id)

        if club.owner_id != owner.id:
            raise Forbidden("Пользователь не является владельцем книжного клуба")

        await self.db.delete(club)
        await self.db.commit()

    async def join_book_club(self, user: DBUser, club_id: int) -> DBBookClub:
        await self.get_book_club(club_id=club_id)

        self.db.add(DBClubMember(club_id=club_id, user_id=user.id))

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise Conflict(errors=["Пользователь уже является участником клуба, повторное добавление не требуется"])

        return await self.get_book_club(club_id=club_id)

    async def remove_member(self, user: DBUser, club_id: int) -> DBBookClub:
        await self.get_book_club(club_id=club_id)

        member = await self.db.get(DBClubMember, {"club_id": club_id, "user_id": user.id})

        if member is None:
            raise Conflict(errors=["Пользователь не состоит в клубе"])

        await self.db.delete(member)
        await self.db.commit()

        return await self.get_book_club(club_id=club_id)
