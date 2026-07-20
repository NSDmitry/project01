from typing import List, Tuple

from sqlalchemy import select, func, or_, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.models import BookClub, ClubMember, Genre, BookClubGenre
from app.bookclubs.schemas import CreateBookClubRequest, BookClubRelation
from app.core.authorization import require_permission
from app.core.errors.errors import NotFound, Conflict
from app.iam.models import User


class BookClubRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_book_club(self, owner: User, model: CreateBookClubRequest, genre_ids: List[int]) -> BookClub:
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
        for genre_id in genre_ids:
            self.db.add(BookClubGenre(club_id=new_book_club.id, genre_id=genre_id))
        await self.db.flush()

        return await self.get_book_club(club_id=new_book_club.id)

    async def get_book_clubs(
        self,
        limit: int,
        offset: int,
        user: User | None = None,
        relation: BookClubRelation | None = None,
        query: str | None = None,
    ) -> Tuple[List[BookClub], int]:
        conditions = []

        if relation == BookClubRelation.owner:
            conditions.append(BookClub.owner_id == user.id)
        elif relation == BookClubRelation.member:
            conditions.append(
                BookClub.id.in_(
                    select(ClubMember.club_id).where(ClubMember.user_id == user.id)
                )
            )

        term = (query or "").strip()
        if term:
            # экранируем спецсимволы LIKE, чтобы искать их как обычный текст
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            # ищем подстроку в названии, описании или в названии/коде любого жанра клуба
            conditions.append(
                or_(
                    BookClub.name.ilike(pattern, escape="\\"),
                    BookClub.description.ilike(pattern, escape="\\"),
                    BookClub.genres.any(
                        or_(
                            Genre.name.ilike(pattern, escape="\\"),
                            Genre.code.ilike(pattern, escape="\\"),
                        )
                    ),
                )
            )

        total = await self.db.scalar(
            select(func.count()).select_from(BookClub).where(*conditions)
        )
        result = await self.db.execute(
            select(BookClub).where(*conditions).order_by(BookClub.id).limit(limit).offset(offset)
        )

        return result.scalars().all(), total

    async def get_book_club(self, club_id: int) -> BookClub:
        result = await self.db.execute(select(BookClub).where(BookClub.id == club_id))
        club = result.scalar_one_or_none()

        if club is None:
            raise NotFound("Книжный клуб с таким id не найден")

        return club

    async def is_member(self, club_id: int, user_id: int) -> bool:
        member = await self.db.get(ClubMember, {"club_id": club_id, "user_id": user_id})

        return member is not None

    async def get_members(self, club_id: int, limit: int, offset: int) -> Tuple[List[int], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(ClubMember).where(ClubMember.club_id == club_id)
        )
        result = await self.db.execute(
            select(ClubMember.user_id)
            .where(ClubMember.club_id == club_id)
            .order_by(ClubMember.user_id)
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    async def handle_user_deleted(self, user_id: int, delete_owned_clubs: bool) -> None:
        # FK на users больше нет - SET NULL/CASCADE, которые раньше делала БД
        # при удалении пользователя, выполняем явно.
        if delete_owned_clubs:
            # вложенное (участники, треды) чистят каскады БД по club_id
            await self.db.execute(delete(BookClub).where(BookClub.owner_id == user_id))
        else:
            await self.db.execute(
                update(BookClub).values(owner_id=None).where(BookClub.owner_id == user_id)
            )
        await self.db.execute(delete(ClubMember).where(ClubMember.user_id == user_id))
        await self.db.flush()

    async def delete_book_club(self, owner: User, club_id: int):
        club = await self.get_book_club(club_id=club_id)

        require_permission(owner, club.owner_id, message="Пользователь не является владельцем книжного клуба")

        await self.db.delete(club)
        await self.db.flush()

    async def set_genres(self, owner: User, club_id: int, genres: List[Genre]) -> BookClub:
        club = await self.get_book_club(club_id=club_id)

        require_permission(owner, club.owner_id, message="Пользователь не является владельцем книжного клуба")

        # club.genres уже загружен selectin-ом, поэтому присваивание считает разницу
        # без ленивой подгрузки: SQLAlchemy сам удалит и добавит строки book_club_genres.
        club.genres = sorted(genres, key=lambda genre: genre.sort_order)
        await self.db.flush()

        return await self.get_book_club(club_id=club_id)

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
