from typing import List, Tuple

from sqlalchemy import select, func, or_, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.models import BookClub, ClubMember, BookClubGenre
from app.bookclubs.schemas import CreateBookClubRequest, BookClubRelation
from app.core.authorization import require_permission
from app.core.contracts import Principal
from app.core.errors.errors import NotFound, Conflict


class BookClubRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_book_club(self, owner: Principal, model: CreateBookClubRequest, genre_ids: List[int]) -> BookClub:
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
            user: Principal | None = None,
            relation: BookClubRelation | None = None,
            query: str | None = None,
            genre_ids: List[int] | None = None,
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
            # ищем подстроку в названии, описании или по жанрам клуба:
            # id подходящих жанров сервис берёт у genres (после распила - у сервиса жанров)
            term_conditions = [
                BookClub.name.ilike(pattern, escape="\\"),
                BookClub.description.ilike(pattern, escape="\\"),
            ]
            if genre_ids:
                term_conditions.append(
                    BookClub.id.in_(
                        select(BookClubGenre.club_id).where(BookClubGenre.genre_id.in_(genre_ids))
                    )
                )
            conditions.append(or_(*term_conditions))

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

    async def handle_user_deleted(self, user_id: int, delete_owned_clubs: bool) -> List[int]:
        # FK на users больше нет - SET NULL/CASCADE, которые раньше делала БД
        # при удалении пользователя, выполняем явно. Возвращаем id удалённых
        # клубов, чтобы threads почистил их треды (FK у тредов тоже нет).
        deleted_club_ids: List[int] = []
        if delete_owned_clubs:
            result = await self.db.execute(
                select(BookClub.id).where(BookClub.owner_id == user_id)
            )
            deleted_club_ids = list(result.scalars().all())
            # участников чистит каскад БД по club_id
            await self.db.execute(delete(BookClub).where(BookClub.owner_id == user_id))
        else:
            await self.db.execute(
                update(BookClub).values(owner_id=None).where(BookClub.owner_id == user_id)
            )
        await self.db.execute(delete(ClubMember).where(ClubMember.user_id == user_id))
        await self.db.flush()

        return deleted_club_ids

    async def delete_book_club(self, owner: Principal, club_id: int):
        club = await self.get_book_club(club_id=club_id)

        require_permission(owner, club.owner_id, message="Пользователь не является владельцем книжного клуба")

        await self.db.delete(club)
        await self.db.flush()

    async def set_genres(self, owner: Principal, club_id: int, genre_ids: List[int]) -> BookClub:
        club = await self.get_book_club(club_id=club_id)

        require_permission(owner, club.owner_id, message="Пользователь не является владельцем книжного клуба")

        await self.db.execute(delete(BookClubGenre).where(BookClubGenre.club_id == club_id))
        for genre_id in genre_ids:
            self.db.add(BookClubGenre(club_id=club_id, genre_id=genre_id))
        await self.db.flush()

        return await self.get_book_club(club_id=club_id)

    async def get_genre_ids(self, club_ids: List[int]) -> dict[int, List[int]]:
        if not club_ids:
            return {}

        result = await self.db.execute(
            select(BookClubGenre.club_id, BookClubGenre.genre_id).where(
                BookClubGenre.club_id.in_(club_ids)
            )
        )

        genre_ids: dict[int, List[int]] = {}
        for club_id, genre_id in result.all():
            genre_ids.setdefault(club_id, []).append(genre_id)

        return genre_ids

    async def change_threads_count(self, club_id: int, delta: int) -> None:
        # GREATEST(...,0) страхует от ухода в минус, если событие продублируется
        # или потеряется (в проде через брокер доставка at-least-once).
        await self.db.execute(
            update(BookClub)
            .where(BookClub.id == club_id)
            .values(threads_count=func.greatest(BookClub.threads_count + delta, 0))
        )
        await self.db.flush()

    async def handle_genres_deleted(self, genre_ids: List[int]) -> None:
        await self.db.execute(delete(BookClubGenre).where(BookClubGenre.genre_id.in_(genre_ids)))
        await self.db.flush()

    async def join_book_club(self, user: Principal, club_id: int) -> BookClub:
        await self.get_book_club(club_id=club_id)

        self.db.add(ClubMember(club_id=club_id, user_id=user.id))

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflict(errors=["Пользователь уже является участником клуба, повторное добавление не требуется"])

        return await self.get_book_club(club_id=club_id)

    async def remove_member(self, user: Principal, club_id: int) -> BookClub:
        await self.get_book_club(club_id=club_id)

        member = await self.db.get(ClubMember, {"club_id": club_id, "user_id": user.id})

        if member is None:
            raise Conflict(errors=["Пользователь не состоит в клубе"])

        await self.db.delete(member)
        await self.db.flush()

        return await self.get_book_club(club_id=club_id)
