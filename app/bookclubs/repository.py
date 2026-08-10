import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, cast

from sqlalchemy import CursorResult, select, func, delete, literal_column, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.bookclubs.models import (
    BookClub,
    BookClubGenre,
    BookNomination,
    ClubMember,
    NominationVote,
    Reading,
    ReadingProgress,
    ReadingStage,
)
from app.bookclubs.schemas import (
    CreateBookClubRequest,
    BookClubRelation,
    ReadingScheduleRequest,
    UpdateBookClubRequest,
)
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
        # Прогресс в заходах и голоса привязаны к пользователю без FK - чистим
        # явно. Заходы и номинации удалённых клубов уносит каскад по club_id.
        await self.db.execute(delete(ReadingProgress).where(ReadingProgress.user_id == user_id))
        await self.db.execute(delete(NominationVote).where(NominationVote.user_id == user_id))
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
        # Прогресс бывшего участника уходит вместе с ним, иначе он продолжал бы
        # попадать в сводку захода, где доля считается от числа участников.
        await self.db.execute(
            delete(ReadingProgress).where(
                ReadingProgress.user_id == user.id,
                ReadingProgress.reading_id.in_(
                    select(Reading.id).where(Reading.club_id == club_id)
                ),
            )
        )
        # Голос бывшего участника - по той же причине: книгу клубу выбирают те,
        # кто в нём состоит.
        await self.db.execute(
            delete(NominationVote).where(
                NominationVote.user_id == user.id, NominationVote.club_id == club_id
            )
        )
        await self.db.flush()

        return await self.get_book_club(club_id=club_id)


class ReadingRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_reading(self, reading_id: int) -> Reading:
        # Всегда через запрос, а не db.get: книга подтягивается selectin-загрузкой
        # при выполнении SELECT, а объект из identity map пришёл бы без неё.
        result = await self.db.execute(select(Reading).where(Reading.id == reading_id))
        reading = result.scalar_one_or_none()

        if reading is None:
            raise NotFound("Заход с таким id не найден")

        return reading

    async def create_reading(self, club_id: int, book_id: int | None, model: ReadingScheduleRequest) -> Reading:
        reading = Reading(
            club_id=club_id,
            book_id=book_id,
            started_at=model.started_at,
            deadline=model.deadline,
        )
        self.db.add(reading)

        try:
            # Незакрытый заход у клуба один - это держит частичный уникальный индекс.
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflict(errors=["У клуба уже есть текущий заход - сначала закройте его"])

        for position, stage in enumerate(model.stages, start=1):
            self.db.add(
                ReadingStage(
                    reading_id=reading.id,
                    position=position,
                    title=stage.title,
                    due_date=stage.due_date,
                    end_page=stage.end_page,
                )
            )
        await self.db.flush()

        return await self.get_reading(reading.id)

    async def get_active_readings(self, club_ids: List[int]) -> List[Reading]:
        if not club_ids:
            return []

        result = await self.db.execute(
            select(Reading).where(Reading.club_id.in_(club_ids), Reading.finished_at.is_(None))
        )

        return list(result.scalars().all())

    async def get_readings(self, club_id: int, limit: int, offset: int) -> Tuple[List[Reading], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(Reading).where(Reading.club_id == club_id)
        )
        result = await self.db.execute(
            select(Reading)
            .where(Reading.club_id == club_id)
            .order_by(Reading.id.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all()), total or 0

    async def finish_reading(self, reading: Reading) -> Reading:
        if reading.finished_at is not None:
            raise Conflict(errors=["Заход уже закрыт"])

        reading.finished_at = datetime.now(timezone.utc)
        await self.db.flush()

        return reading

    async def get_stages(self, reading_ids: List[int]) -> Dict[int, List[ReadingStage]]:
        if not reading_ids:
            return {}

        result = await self.db.execute(
            select(ReadingStage)
            .where(ReadingStage.reading_id.in_(reading_ids))
            .order_by(ReadingStage.reading_id, ReadingStage.position)
        )

        stages: Dict[int, List[ReadingStage]] = {}
        for stage in result.scalars().all():
            stages.setdefault(stage.reading_id, []).append(stage)

        return stages

    async def get_stage_club_id(self, stage_id: int) -> Optional[int]:
        """id клуба, которому принадлежит этап, либо None - этапа нет."""
        club_id: Optional[int] = await self.db.scalar(
            select(Reading.club_id)
            .join(ReadingStage, ReadingStage.reading_id == Reading.id)
            .where(ReadingStage.id == stage_id)
        )

        return club_id

    async def set_progress(
        self, reading_id: int, user_id: int, stage_id: int | None, page: int | None
    ) -> ReadingProgress:
        # Upsert: у участника одна строка прогресса на заход, повторная отметка
        # переписывает её, а не падает об уникальный ключ. updated_at ставим явно -
        # onupdate работает только на пути ORM, а не в INSERT ... ON CONFLICT.
        statement = pg_insert(ReadingProgress).values(
            reading_id=reading_id, user_id=user_id, stage_id=stage_id, page=page
        )
        await self.db.execute(
            statement.on_conflict_do_update(
                constraint="uq_reading_progress_reading_id_user_id",
                set_={
                    "stage_id": statement.excluded.stage_id,
                    "page": statement.excluded.page,
                    "updated_at": func.now(),
                },
            )
        )
        await self.db.flush()

        progress = await self.get_progress(reading_id, user_id)
        if progress is None:
            raise NotFound("Прогресс не найден")

        return progress

    async def get_progress(self, reading_id: int, user_id: int) -> Optional[ReadingProgress]:
        result = await self.db.execute(
            select(ReadingProgress).where(
                ReadingProgress.reading_id == reading_id, ReadingProgress.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    async def get_progress_page(
        self, reading_id: int, limit: int, offset: int
    ) -> Tuple[List[ReadingProgress], int]:
        total = await self.db.scalar(
            select(func.count()).select_from(ReadingProgress).where(
                ReadingProgress.reading_id == reading_id
            )
        )
        result = await self.db.execute(
            select(ReadingProgress)
            .where(ReadingProgress.reading_id == reading_id)
            .order_by(ReadingProgress.updated_at.desc(), ReadingProgress.id.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all()), total or 0

    async def get_expected_positions(self, reading_ids: List[int], today: date) -> Dict[int, int]:
        """Последний этап каждого захода, чья дата уже наступила.

        Заходы без наступивших этапов в ответе отсутствуют - сверять прогресс
        ещё не с чем.
        """
        if not reading_ids:
            return {}

        result = await self.db.execute(
            select(ReadingStage.reading_id, func.max(ReadingStage.position))
            .where(ReadingStage.reading_id.in_(reading_ids), ReadingStage.due_date <= today)
            .group_by(ReadingStage.reading_id)
        )

        return dict(result.tuples().all())

    async def count_on_track(self, expected_positions: Dict[int, int]) -> Dict[int, int]:
        """Сколько участников каждого захода закрыли этап не ниже ожидаемого."""
        if not expected_positions:
            return {}

        # Группировка по (заход, этап) отдаёт единицы строк на заход - порог
        # применяем в Python, чтобы не собирать запрос с разным условием на каждый заход.
        result = await self.db.execute(
            select(ReadingProgress.reading_id, ReadingStage.position, func.count())
            .join(ReadingStage, ReadingStage.id == ReadingProgress.stage_id)
            .where(ReadingProgress.reading_id.in_(list(expected_positions)))
            .group_by(ReadingProgress.reading_id, ReadingStage.position)
        )

        counts: Dict[int, int] = {}
        for reading_id, position, count in result.tuples().all():
            if position >= expected_positions[reading_id]:
                counts[reading_id] = counts.get(reading_id, 0) + count

        return counts


class NominationRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_nomination(self, club_id: int, book_id: int) -> BookNomination:
        nomination = BookNomination(club_id=club_id, book_id=book_id)
        self.db.add(nomination)

        try:
            # Одна книга в клубе номинируется один раз - это держит уникальный ключ.
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflict(errors=["Эта книга уже номинирована в клубе"])

        return await self.get_nomination(nomination.id)

    async def get_nomination(self, nomination_id: int) -> BookNomination:
        # Запросом, а не db.get: книгу подтягивает selectin-загрузка при SELECT,
        # объект из identity map пришёл бы без неё.
        result = await self.db.execute(
            select(BookNomination).where(BookNomination.id == nomination_id)
        )
        nomination = result.scalar_one_or_none()

        if nomination is None:
            raise NotFound("Номинация с таким id не найдена")

        return nomination

    async def get_nominations(self, club_id: int) -> List[BookNomination]:
        result = await self.db.execute(
            select(BookNomination)
            .where(BookNomination.club_id == club_id)
            .order_by(BookNomination.id)
        )

        return list(result.scalars().all())

    async def count_votes(self, club_id: int) -> Dict[int, int]:
        """Число голосов по каждой номинации клуба; без голосов - ключа нет."""
        result = await self.db.execute(
            select(NominationVote.nomination_id, func.count())
            .where(NominationVote.club_id == club_id)
            .group_by(NominationVote.nomination_id)
        )

        return dict(result.tuples().all())

    async def get_vote(self, club_id: int, user_id: int) -> Optional[NominationVote]:
        return await self.db.get(NominationVote, {"user_id": user_id, "club_id": club_id})

    async def set_vote(self, club_id: int, user_id: int, nomination_id: int) -> None:
        # Upsert по PK (user_id, club_id): голос за другую номинацию переставляет
        # тот же голос, повторный за ту же - ничего не меняет. Проверка «уже
        # голосовал» в коде здесь не нужна и была бы гонкой.
        statement = pg_insert(NominationVote).values(
            user_id=user_id, club_id=club_id, nomination_id=nomination_id
        )
        await self.db.execute(
            statement.on_conflict_do_update(
                index_elements=["user_id", "club_id"],
                set_={"nomination_id": statement.excluded.nomination_id},
            )
        )
        await self.db.flush()

    async def delete_vote(self, club_id: int, user_id: int, nomination_id: int) -> bool:
        """Снять голос с номинации. False - голоса за неё не было."""
        result = await self.db.execute(
            delete(NominationVote).where(
                NominationVote.user_id == user_id,
                NominationVote.club_id == club_id,
                NominationVote.nomination_id == nomination_id,
            )
        )
        await self.db.flush()

        # DELETE возвращает CursorResult, но перегрузка execute() объявляет Result[Any].
        return cast(CursorResult, result).rowcount > 0

    async def clear_nominations(self, club_id: int) -> None:
        # Голоса уносит каскад по nomination_id.
        await self.db.execute(delete(BookNomination).where(BookNomination.club_id == club_id))
        await self.db.flush()
