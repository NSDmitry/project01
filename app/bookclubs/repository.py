import re
from typing import Any, List, Tuple

from sqlalchemy import select, func, delete, literal_column, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.bookclubs.models import BookClub, ClubMember, BookClubGenre
from app.bookclubs.schemas import CreateBookClubRequest, BookClubRelation, UpdateBookClubRequest
from app.core.authorization import require_permission
from app.core.contracts import Principal
from app.core.errors.errors import NotFound, Conflict

# Слова поискового запроса. Всё, что не \w, отбрасывается - в том числе
# спецсимволы tsquery (& | ! ( ) : *), поэтому собранная ниже строка не может
# сломать разбор запроса или подмешать в него чужой оператор.
_WORD = re.compile(r"\w+", re.UNICODE)


def _tsquery(term: str | None) -> ColumnElement[Any] | None:
    """Поисковый запрос пользователя как tsquery, либо None если искать нечего.

    Каждое слово ищется по префиксу (`:*`): подстрочный ILIKE находил «фантаст»
    внутри «фантастики», и без префикса FTS такой запрос бы потерял. Середину
    слова FTS всё равно не найдёт - это осознанная плата за словоформы и
    ранжирование.

    Конфигурация 'russian' подставляется литералом, а не параметром: тип
    regconfig драйвер передать не умеет. Сам текст запроса - обычный bind-параметр.
    """
    tokens = _WORD.findall(term or "")
    if not tokens:
        return None

    # to_tsquery прогоняет каждое слово через словари конфигурации, поэтому
    # запрос нормализуется той же морфологией, что и search_vector.
    return func.to_tsquery(literal_column("'russian'"), " & ".join(f"{t}:*" for t in tokens))


class BookClubRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_book_club(self, owner: Principal, model: CreateBookClubRequest, genre_ids: List[int]) -> BookClub:
        new_book_club = BookClub()
        new_book_club.name = model.name
        new_book_club.description = model.description
        new_book_club.owner_id = owner.id
        new_book_club.members_count = 1

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
        conditions: List[ColumnElement[bool]] = []

        if relation is not None:
            # Фильтр «мои клубы» без пользователя молча вернул бы весь каталог -
            # падаем, а не отдаём лишнее.
            if user is None:
                raise ValueError("Фильтр по relation требует авторизованного пользователя")

            if relation == BookClubRelation.owner:
                conditions.append(BookClub.owner_id == user.id)
            elif relation == BookClubRelation.member:
                conditions.append(
                    BookClub.id.in_(
                        select(ClubMember.club_id).where(ClubMember.user_id == user.id)
                    )
                )

        if genre_ids:
            conditions.append(
                BookClub.id.in_(
                    select(BookClubGenre.club_id).where(BookClubGenre.genre_id.in_(genre_ids))
                )
            )

        # По умолчанию порядок по id: без поискового запроса ранжировать нечем.
        order_by: Tuple[Any, ...] = (BookClub.id,)
        tsquery = _tsquery(query)
        if tsquery is not None:
            conditions.append(BookClub.search_vector.bool_op("@@")(tsquery))
            # id вторым ключом - тай-брейк при равном ранге, иначе соседние
            # страницы могут вернуть одну и ту же строку дважды.
            order_by = (func.ts_rank(BookClub.search_vector, tsquery).desc(), BookClub.id)

        total = await self.db.scalar(
            select(func.count()).select_from(BookClub).where(*conditions)
        )
        result = await self.db.execute(
            select(BookClub).where(*conditions).order_by(*order_by).limit(limit).offset(offset)
        )

        return list(result.scalars().all()), total or 0

    async def get_book_club(self, club_id: int) -> BookClub:
        result = await self.db.execute(select(BookClub).where(BookClub.id == club_id))
        club = result.scalar_one_or_none()

        if club is None:
            raise NotFound("Книжный клуб с таким id не найден")

        return club

    async def is_member(self, club_id: int, user_id: int) -> bool:
        member = await self.db.get(ClubMember, {"club_id": club_id, "user_id": user_id})

        return member is not None

    # Общее число участников не считаем: его держит BookClub.members_count,
    # а клуб сервис к этому моменту уже загрузил.
    async def get_members(self, club_id: int, limit: int, offset: int) -> List[int]:
        result = await self.db.execute(
            select(ClubMember.user_id)
            .where(ClubMember.club_id == club_id)
            .order_by(ClubMember.user_id)
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all())

    async def _change_members_count(self, club_id: int, delta: int) -> None:
        # Инкремент считает БД, а не Python: параллельные join/leave по одному клубу
        # иначе затирали бы друг друга (прочитали 5 - оба записали 6).
        # synchronize_session="fetch" помечает уже загруженный объект клуба
        # просроченным, иначе get_book_club отдал бы его из identity map со старым
        # счётчиком.
        await self.db.execute(
            update(BookClub)
            .where(BookClub.id == club_id)
            .values(members_count=func.greatest(BookClub.members_count + delta, 0))
            .execution_options(synchronize_session="fetch")
        )

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
        # Счётчик уменьшаем до удаления строк: после DELETE подзапрос уже не найдёт,
        # в каких клубах пользователь состоял. В клубе он максимум один раз (PK),
        # поэтому ровно -1 на затронутый клуб. Удалённые выше клубы под UPDATE не
        # попадут - их строк уже нет.
        await self.db.execute(
            update(BookClub)
            .where(
                BookClub.id.in_(
                    select(ClubMember.club_id).where(ClubMember.user_id == user_id)
                )
            )
            .values(members_count=func.greatest(BookClub.members_count - 1, 0))
        )
        await self.db.execute(delete(ClubMember).where(ClubMember.user_id == user_id))
        await self.db.flush()

        return deleted_club_ids

    async def delete_book_club(self, owner: Principal, club_id: int) -> None:
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

    async def update_book_club(self, owner: Principal, club_id: int, model: UpdateBookClubRequest) -> BookClub:
        club = await self.get_book_club(club_id=club_id)

        require_permission(
            owner,
            club.owner_id,
            message="Пользователь не является владельцем книжного клуба"
        )

        if model.name is not None:
            club.name = model.name

        if model.description is not None:
            club.description = model.description

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()

            raise Conflict(
                message="Клуб с таким названием уже существует",
                errors=["field: name, message: Это имя уже используется"],
            )

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

        await self._change_members_count(club_id, +1)

        return await self.get_book_club(club_id=club_id)

    async def remove_member(self, user: Principal, club_id: int) -> BookClub:
        await self.get_book_club(club_id=club_id)

        member = await self.db.get(ClubMember, {"club_id": club_id, "user_id": user.id})

        if member is None:
            raise Conflict(errors=["Пользователь не состоит в клубе"])

        await self.db.delete(member)
        await self._change_members_count(club_id, -1)
        await self.db.flush()

        return await self.get_book_club(club_id=club_id)
