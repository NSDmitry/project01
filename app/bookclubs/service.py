from datetime import date
from typing import Dict, List, Optional, Tuple

from app.bookclubs.models import BookClub, Reading, ReadingStage
from app.bookclubs.repository import BookClubRepository, ReadingRepository
from app.bookclubs.schemas import (
    CreateBookClubRequest,
    CreateReadingRequest,
    CurrentReadingResponse,
    CurrentReadingSummary,
    ReadingProgressResponse,
    ReadingProgressSummary,
    ReadingResponse,
    ReadingStageResponse,
    UpdateBookClubGenresRequest,
    SearchBookClubsRequest,
    UpdateBookClubRequest,
    UpdateReadingProgressRequest,
    BookClubResponse,
)
from app.bookclubs.ports import BooksPort, GenresPort, UsersPort
from app.core import events
from app.core.authorization import require_permission
from app.core.contracts import BookResponse, GenreResponse, Principal, UserSummary
from app.core.errors.errors import Conflict, Forbidden, NotFound, UnprocessableEntity
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel


async def _progress_summaries(
    reading_repository: ReadingRepository,
    readings: List[Reading],
    members_by_club: Dict[int, int],
) -> Tuple[Dict[int, ReadingProgressSummary], Dict[int, int]]:
    """Сводки «сколько участников в графике» по каждому заходу.

    Вторым значением - ожидаемая позиция этапа по заходам: она же нужна, чтобы
    отметить в графике отдельного участника, и считается тем же запросом.
    """
    reading_ids = [reading.id for reading in readings]
    expected_positions = await reading_repository.get_expected_positions(reading_ids, date.today())
    on_track_counts = await reading_repository.count_on_track(expected_positions)

    summaries: Dict[int, ReadingProgressSummary] = {}
    for reading in readings:
        members_count = members_by_club.get(reading.club_id, 0)
        if reading.id not in expected_positions:
            # Срок первого этапа ещё не наступил (или этапов нет) - отставать не от чего.
            on_track_count = members_count
        else:
            # Прогресс участника, вышедшего из клуба, удаляется - но между двумя
            # запросами он мог ещё не уйти, и доля вышла бы больше единицы.
            on_track_count = min(on_track_counts.get(reading.id, 0), members_count)

        summaries[reading.id] = ReadingProgressSummary(
            members_count=members_count,
            on_track_count=on_track_count,
            on_track_ratio=round(on_track_count / members_count, 2) if members_count else 0.0,
        )

    return summaries, expected_positions


class BookClubService:
    book_club_repository: BookClubRepository
    reading_repository: ReadingRepository
    genre_repository: GenresPort
    user_repository: UsersPort

    def __init__(
        self,
        book_club_repository: BookClubRepository,
        reading_repository: ReadingRepository,
        genre_repository: GenresPort,
        user_repository: UsersPort,
    ) -> None:
        self.book_club_repository = book_club_repository
        self.reading_repository = reading_repository
        self.genre_repository = genre_repository
        self.user_repository = user_repository

    # owner, genres и members_count не живут в модели клуба - подтягиваем их
    # батчем (owner и genres из iam/genres, после распила - вызовы соседних
    # сервисов), одним запросом на всю страницу вместо N+1. threads_count -
    # денормализованный столбец, который ведёт домен клубов по событиям тредов
    # (см. events.py).
    async def _to_responses(self, clubs: List[BookClub]) -> List[BookClubResponse]:
        owners = await self._owners_by_id(clubs)
        genres_by_club = await self._genres_by_club(clubs)
        readings_by_club = await self._current_readings_by_club(clubs)

        responses = []
        for club in clubs:
            response = BookClubResponse.model_validate(club)
            response.owner = owners.get(club.owner_id) if club.owner_id is not None else None
            response.genres = genres_by_club.get(club.id, [])
            response.current_reading = readings_by_club.get(club.id)
            responses.append(response)

        return responses

    # Текущий заход в карточке клуба - книга и доля участников в графике. Тоже
    # батчем: три запроса на страницу клубов независимо от её размера.
    async def _current_readings_by_club(self, clubs: List[BookClub]) -> dict[int, CurrentReadingSummary]:
        readings = await self.reading_repository.get_active_readings([club.id for club in clubs])
        if not readings:
            return {}

        summaries, _ = await _progress_summaries(
            self.reading_repository, readings, {club.id: club.members_count for club in clubs}
        )

        return {
            reading.club_id: CurrentReadingSummary(
                id=reading.id,
                book=BookResponse.model_validate(reading.book) if reading.book else None,
                deadline=reading.deadline,
                on_track_ratio=summaries[reading.id].on_track_ratio,
            )
            for reading in readings
        }

    async def _to_response(self, club: BookClub) -> BookClubResponse:
        return (await self._to_responses([club]))[0]

    async def _owners_by_id(self, clubs: List[BookClub]) -> dict[int, UserSummary]:
        owner_ids = {club.owner_id for club in clubs if club.owner_id is not None}
        if not owner_ids:
            return {}

        summaries = await self.user_repository.get_summaries_by_ids(list(owner_ids))
        return {summary.id: summary for summary in summaries}

    async def _genres_by_club(self, clubs: List[BookClub]) -> dict[int, List[GenreResponse]]:
        genre_ids_by_club = await self.book_club_repository.get_genre_ids([club.id for club in clubs])
        all_genre_ids = {gid for ids in genre_ids_by_club.values() for gid in ids}

        # get_by_ids отдаёт жанры уже в порядке sort_order - перебирая их для
        # каждого клуба, получаем жанры клуба сразу отсортированными.
        genres = await self.genre_repository.get_by_ids(list(all_genre_ids))

        genres_by_club: dict[int, List[GenreResponse]] = {}
        for club_id, ids in genre_ids_by_club.items():
            club_genre_ids = set(ids)
            genres_by_club[club_id] = [genre for genre in genres if genre.id in club_genre_ids]

        return genres_by_club

    async def create_book_club(self, model: CreateBookClubRequest, owner: Principal) -> ResponseModel[BookClubResponse]:
        genres = await self._resolve_genres(model.genres)

        db_book_club: BookClub = await self.book_club_repository.create_book_club(
            owner, model, [genre.id for genre in genres]
        )

        return ResponseModel.ok(await self._to_response(db_book_club))

    async def set_genres(
        self, owner: Principal, club_id: int, model: UpdateBookClubGenresRequest
    ) -> ResponseModel[BookClubResponse]:
        genres = await self._resolve_genres(model.genres)

        db_book_club: BookClub = await self.book_club_repository.set_genres(
            owner, club_id, [genre.id for genre in genres]
        )

        return ResponseModel.ok(await self._to_response(db_book_club))

    async def update_book_club(
            self,
            owner: Principal,
            club_id: int,
            model: UpdateBookClubRequest
    ) -> ResponseModel[BookClubResponse]:
        club = await self.book_club_repository.update_book_club(owner, club_id, model)
        return ResponseModel.ok(await self._to_response(club))

    async def _resolve_genres(self, codes: List[str]) -> List[GenreResponse]:
        unique_codes = list(dict.fromkeys(codes))
        genres: List[GenreResponse] = await self.genre_repository.get_by_codes(unique_codes)

        found = {genre.code for genre in genres}
        missing = [code for code in unique_codes if code not in found]
        if missing:
            raise UnprocessableEntity(
                message="Неизвестный жанр",
                errors=[f"field: genres, message: неизвестный жанр {code}" for code in missing],
            )

        return genres

    async def get_book_clubs(self, limit: int, offset: int) -> ResponseModel[Page[BookClubResponse]]:
        db_clubs, total = await self.book_club_repository.get_book_clubs(limit, offset)

        return await self._page(db_clubs, total, limit, offset)

    async def search_book_clubs(
        self, user: Principal, model: SearchBookClubsRequest
    ) -> ResponseModel[Page[BookClubResponse]]:
        # Коды жанров превращаем в id у genres (после распила - вызов сервиса
        # жанров). Неизвестный код - ошибка валидации, а не молча пустая выдача.
        genres = await self._resolve_genres(model.genres) if model.genres else []

        db_clubs, total = await self.book_club_repository.get_book_clubs(
            model.limit,
            model.offset,
            user,
            model.relation,
            model.query,
            [genre.id for genre in genres],
        )

        return await self._page(db_clubs, total, model.limit, model.offset)

    async def _page(
        self, db_clubs: List[BookClub], total: int, limit: int, offset: int
    ) -> ResponseModel[Page[BookClubResponse]]:
        page = Page(
            items=await self._to_responses(db_clubs),
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def get_book_club(self, club_id: int) -> ResponseModel[BookClubResponse]:
        db_club: BookClub = await self.book_club_repository.get_book_club(club_id)

        return ResponseModel.ok(await self._to_response(db_club))

    async def get_members(self, club_id: int, limit: int, offset: int) -> ResponseModel[Page[UserSummary]]:
        club = await self.book_club_repository.get_book_club(club_id)
        user_ids = await self.book_club_repository.get_members(club_id, limit=limit, offset=offset)

        page = Page(
            items=await self.user_repository.get_summaries_by_ids(user_ids),
            total=club.members_count,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def delete_book_club(self, owner: Principal, book_club_id: int) -> ResponseModel:
        await self.book_club_repository.delete_book_club(owner, book_club_id)
        # FK threads.club_id больше нет - треды удалённого клуба чистит
        # threads по событию
        await events.publish(events.CLUBS_DELETED, {"club_ids": [book_club_id]})

        return ResponseModel.ok(message="Книжный клуб успешно удален")

    async def join(self, user: Principal, club_id: int) -> ResponseModel[BookClubResponse]:
        db_club: BookClub = await self.book_club_repository.join_book_club(user=user, club_id=club_id)
        club = await self._to_response(db_club)

        return ResponseModel.ok(club)

    async def leave(self, user: Principal, club_id: int) -> ResponseModel[BookClubResponse]:
        db_club: BookClub = await self.book_club_repository.remove_member(user, club_id)
        club = await self._to_response(db_club)

        return ResponseModel.ok(club)


class ReadingService:
    reading_repository: ReadingRepository
    book_club_repository: BookClubRepository
    book_service: BooksPort
    user_repository: UsersPort

    def __init__(
        self,
        reading_repository: ReadingRepository,
        book_club_repository: BookClubRepository,
        book_service: BooksPort,
        user_repository: UsersPort,
    ) -> None:
        self.reading_repository = reading_repository
        self.book_club_repository = book_club_repository
        self.book_service = book_service
        self.user_repository = user_repository

    # Этапы - отдельная таблица, тянем их батчем на всю страницу заходов.
    async def _to_responses(self, readings: List[Reading]) -> List[ReadingResponse]:
        stages_by_reading = await self.reading_repository.get_stages(
            [reading.id for reading in readings]
        )

        responses = []
        for reading in readings:
            response = ReadingResponse.model_validate(reading)
            response.stages = [
                ReadingStageResponse.model_validate(stage)
                for stage in stages_by_reading.get(reading.id, [])
            ]
            responses.append(response)

        return responses

    async def _to_response(self, reading: Reading) -> ReadingResponse:
        return (await self._to_responses([reading]))[0]

    async def create_reading(
        self, owner: Principal, club_id: int, model: CreateReadingRequest
    ) -> ResponseModel[ReadingResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        # Модераторов в клубе пока нет - заход заводит владелец (или админ).
        require_permission(owner, club.owner_id, message="Создавать заход может только владелец клуба")

        book = await self.book_service.get_or_create_book(model.book_volume_id)
        reading = await self.reading_repository.create_reading(club_id, book.id, model)

        return ResponseModel.ok(await self._to_response(reading))

    async def get_current_reading(self, club_id: int) -> ResponseModel[CurrentReadingResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        readings = await self.reading_repository.get_active_readings([club_id])

        if not readings:
            raise NotFound("У клуба нет текущего захода")

        reading = readings[0]
        summaries, expected_positions = await _progress_summaries(
            self.reading_repository, [reading], {club_id: club.members_count}
        )
        response = await self._to_response(reading)

        summary = summaries[reading.id]
        expected_position = expected_positions.get(reading.id)
        summary.current_stage = next(
            (stage for stage in response.stages if stage.position == expected_position), None
        )

        return ResponseModel.ok(CurrentReadingResponse(reading=response, progress=summary))

    async def get_readings(self, club_id: int, limit: int, offset: int) -> ResponseModel[Page[ReadingResponse]]:
        await self.book_club_repository.get_book_club(club_id)
        readings, total = await self.reading_repository.get_readings(club_id, limit, offset)

        page = Page(
            items=await self._to_responses(readings),
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def finish_reading(self, owner: Principal, reading_id: int) -> ResponseModel[ReadingResponse]:
        reading = await self.reading_repository.get_reading(reading_id)
        club = await self.book_club_repository.get_book_club(reading.club_id)

        require_permission(owner, club.owner_id, message="Закрывать заход может только владелец клуба")

        reading = await self.reading_repository.finish_reading(reading)

        return ResponseModel.ok(await self._to_response(reading))

    # Прогресс - это последний закрытый этап. Если участник прислал только страницу,
    # закрытыми считаются все этапы, чья последняя страница уже прочитана.
    @staticmethod
    def _resolve_stage(
        model: UpdateReadingProgressRequest, stages: List[ReadingStage]
    ) -> Optional[ReadingStage]:
        if model.stage_id is not None:
            stage = next((stage for stage in stages if stage.id == model.stage_id), None)
            if stage is None:
                raise NotFound(errors=["Этап с таким id не найден в этом заходе"])

            return stage

        reached = [
            stage for stage in stages
            if stage.end_page is not None and model.page is not None and stage.end_page <= model.page
        ]

        return reached[-1] if reached else None

    async def set_progress(
        self, user: Principal, reading_id: int, model: UpdateReadingProgressRequest
    ) -> ResponseModel[ReadingProgressResponse]:
        reading = await self.reading_repository.get_reading(reading_id)

        if not await self.book_club_repository.is_member(reading.club_id, user.id):
            raise Forbidden(errors=["Отмечать прогресс могут только участники клуба"])

        if reading.finished_at is not None:
            raise Conflict(errors=["Заход закрыт - прогресс больше не меняется"])

        stages = (await self.reading_repository.get_stages([reading_id])).get(reading_id, [])
        stage = self._resolve_stage(model, stages)

        progress = await self.reading_repository.set_progress(
            reading_id, user.id, stage.id if stage else None, model.page
        )
        expected_positions = await self.reading_repository.get_expected_positions(
            [reading_id], date.today()
        )
        summaries = await self.user_repository.get_summaries_by_ids([user.id])

        return ResponseModel.ok(
            ReadingProgressResponse(
                user=summaries[0] if summaries else None,
                stage=ReadingStageResponse.model_validate(stage) if stage else None,
                page=progress.page,
                on_track=self._is_on_track(stage, expected_positions.get(reading_id)),
                updated_at=progress.updated_at,
            )
        )

    @staticmethod
    def _is_on_track(stage: Optional[ReadingStage], expected_position: Optional[int]) -> bool:
        # Ни один срок не наступил - в графике все, даже те, кто ничего не отметил.
        if expected_position is None:
            return True

        return stage is not None and stage.position >= expected_position

    async def get_progress(
        self, reading_id: int, limit: int, offset: int
    ) -> ResponseModel[Page[ReadingProgressResponse]]:
        await self.reading_repository.get_reading(reading_id)
        rows, total = await self.reading_repository.get_progress_page(reading_id, limit, offset)

        stages = {
            stage.id: stage
            for stage in (await self.reading_repository.get_stages([reading_id])).get(reading_id, [])
        }
        expected_position = (
            await self.reading_repository.get_expected_positions([reading_id], date.today())
        ).get(reading_id)

        summaries = await self.user_repository.get_summaries_by_ids([row.user_id for row in rows])
        users = {summary.id: summary for summary in summaries}

        items = []
        for row in rows:
            stage = stages.get(row.stage_id) if row.stage_id is not None else None
            items.append(
                ReadingProgressResponse(
                    user=users.get(row.user_id),
                    stage=ReadingStageResponse.model_validate(stage) if stage else None,
                    page=row.page,
                    on_track=self._is_on_track(stage, expected_position),
                    updated_at=row.updated_at,
                )
            )

        return ResponseModel.ok(Page(items=items, total=total, limit=limit, offset=offset))
