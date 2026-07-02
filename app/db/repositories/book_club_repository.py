from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.errors import NotFound, Forbidden, Conflict
from app.db.models.db_user import User
from app.db.models.db_book_club import BookClub
from app.db.models.db_club_member import ClubMember
from app.schemas.book_club_schema import CreateBookClubRequest, BookClubRelation


class BookClubRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_book_club(self, owner: User, model: CreateBookClubRequest) -> BookClub:
        new_book_club = BookClub()
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

        self.db.add(ClubMember(club_id=new_book_club.id, user_id=owner.id))
        await self.db.flush()

        return await self.get_book_club(club_id=new_book_club.id)

    async def get_book_clubs(self, user: User, relation: BookClubRelation | None = None) -> List[BookClub]:
        query = select(BookClub)

        if relation == BookClubRelation.owner:
            query = query.where(BookClub.owner_id == user.id)
        elif relation == BookClubRelation.member:
            query = query.where(
                BookClub.id.in_(
                    select(ClubMember.club_id).where(ClubMember.user_id == user.id)
                )
            )

        result = await self.db.execute(query)

        return result.scalars().all()

    async def get_book_club(self, club_id: int) -> BookClub:
        result = await self.db.execute(select(BookClub).where(BookClub.id == club_id))
        club = result.scalar_one_or_none()

        if club is None:
            raise NotFound("Книжный клуб с таким id не найден")

        return club

    async def is_member(self, club_id: int, user_id: int) -> bool:
        member = await self.db.get(ClubMember, {"club_id": club_id, "user_id": user_id})

        return member is not None

    async def get_members(self, club_id: int, limit: int, offset: int) -> Tuple[List[User], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(ClubMember).where(ClubMember.club_id == club_id)
        )
        result = await self.db.execute(
            select(User)
            .join(ClubMember, ClubMember.user_id == User.id)
            .where(ClubMember.club_id == club_id)
            .order_by(User.id)
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    async def delete_book_club(self, owner: User, club_id: int):
        club = await self.get_book_club(club_id=club_id)

        if club.owner_id != owner.id:
            raise Forbidden("Пользователь не является владельцем книжного клуба")

        await self.db.delete(club)
        await self.db.flush()

    async def join_book_club(self, user: User, club_id: int) -> BookClub:
        await self.get_book_club(club_id=club_id)

        self.db.add(ClubMember(club_id=club_id, user_id=user.id))

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflict(errors=["Пользователь уже является участником клуба, повторное добавление не требуется"])

        return await self.get_book_club(club_id=club_id)

    async def remove_member(self, user: User, club_id: int) -> BookClub:
        await self.get_book_club(club_id=club_id)

        member = await self.db.get(ClubMember, {"club_id": club_id, "user_id": user.id})

        if member is None:
            raise Conflict(errors=["Пользователь не состоит в клубе"])

        await self.db.delete(member)
        await self.db.flush()

        return await self.get_book_club(club_id=club_id)
