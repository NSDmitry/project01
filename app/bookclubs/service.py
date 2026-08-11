from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile

from app.bookclubs.models import BookClub, BookNomination, ClubJoinRequest, Reading, ReadingStage
from app.bookclubs.repository import BookClubRepository, NominationRepository, ReadingRepository
from app.bookclubs.schemas import (
    ClubMemberResponse,
    ClubPrivacy,
    ClubRole,
    CreateBookClubRequest,
    CreateInviteRequest,
    CreateNominationRequest,
    CreateReadingRequest,
    CurrentReadingResponse,
    CurrentReadingSummary,
    InviteResponse,
    JoinByInviteRequest,
    JoinRequestResponse,
    JoinRequestStatus,
    NominationResponse,
    ReadingProgressResponse,
    ReadingProgressSummary,
    ReadingResponse,
    ReadingScheduleRequest,
    ReadingStageResponse,
    TransferOwnershipRequest,
    UpdateBookClubGenresRequest,
    UpdateMemberRoleRequest,
    SearchBookClubsRequest,
    UpdateBookClubRequest,
    UpdateReadingProgressRequest,
    BookClubResponse,
)
from app.books.service import BookService
from app.core import media
from app.core.authorization import require_permission
from app.core.contracts import BookResponse, GenreResponse, Principal, UserSummary
from app.core.errors.errors import Conflict, Forbidden, NotFound, UnprocessableEntity
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.genres.repository import GenreRepository
from app.iam.repository import UserRepository

_CLOSED_CLUB_MESSAGES = {
    ClubPrivacy.by_request.value: "В этот клуб можно вступить только по заявке",
    ClubPrivacy.by_invite.value: "В этот клуб можно вступить только по приглашению",
}
# Владелец всегда в составе клуба: и выход, и исключение упираются в один запрет.
_OWNER_STAYS_MESSAGE = "Владелец не может покинуть клуб - сначала передайте клуб"


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


async def _reading_responses(
    reading_repository: ReadingRepository, readings: List[Reading]
) -> List[ReadingResponse]:
    """Заходы с этапами. Этапы - отдельная таблица, тянем их батчем на всю страницу."""
    stages_by_reading = await reading_repository.get_stages([reading.id for reading in readings])

    responses = []
    for reading in readings:
        response = ReadingResponse.model_validate(reading)
        response.stages = [
            ReadingStageResponse.model_validate(stage)
            for stage in stages_by_reading.get(reading.id, [])
        ]
        responses.append(response)

    return responses


class BookClubService:
    book_club_repository: BookClubRepository
    reading_repository: ReadingRepository
    genre_repository: GenreRepository
    user_repository: UserRepository

    def __init__(
        self,
        book_club_repository: BookClubRepository,
        reading_repository: ReadingRepository,
        genre_repository: GenreRepository,
        user_repository: UserRepository,
    ) -> None:
        self.book_club_repository = book_club_repository
        self.reading_repository = reading_repository
        self.genre_repository = genre_repository
        self.user_repository = user_repository

    # owner, genres и members_count не живут в модели клуба - подтягиваем их
    # батчем (owner и genres из iam/genres), одним запросом на всю страницу
    # вместо N+1. threads_count - денормализованный столбец, который домены
    # тредов и аккаунтов правят прямым вызовом change_threads_count.
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
        club = await self.book_club_repository.get_book_club(club_id)
        require_permission(owner, club.owner_id, message="Пользователь не является владельцем книжного клуба")

        genres = await self._resolve_genres(model.genres)

        db_book_club: BookClub = await self.book_club_repository.set_genres(
            club, [genre.id for genre in genres]
        )

        return ResponseModel.ok(await self._to_response(db_book_club))

    async def update_book_club(
            self,
            owner: Principal,
            club_id: int,
            model: UpdateBookClubRequest
    ) -> ResponseModel[BookClubResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        require_permission(owner, club.owner_id, message="Пользователь не является владельцем книжного клуба")

        club = await self.book_club_repository.update_book_club(club, model)
        return ResponseModel.ok(await self._to_response(club))

    async def update_cover(
            self,
            owner: Principal,
            club_id: int,
            file: UploadFile
    ) -> ResponseModel[BookClubResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        # Права проверяем до обработки файла: иначе чужая загрузка успевала бы
        # занять место в хранилище и осиротеть там вместе с ответом 403.
        require_permission(owner, club.owner_id, message="Пользователь не является владельцем книжного клуба")

        previous_key = club.cover_key
        cover_key = await media.store_image(media.CLUB_COVERS, file)
        db_club: BookClub = await self.book_club_repository.update_cover(club, cover_key)
        # ponytail: как и с аватаром - старый файл удаляем до коммита. Упавший
        # коммит оставит ссылку на удалённый файл; хранилище важнее.
        await media.delete_image(previous_key)

        return ResponseModel.ok(await self._to_response(db_club))

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

    async def get_members(self, club_id: int, limit: int, offset: int) -> ResponseModel[Page[ClubMemberResponse]]:
        club = await self.book_club_repository.get_book_club(club_id)
        members = await self.book_club_repository.get_members(club_id, limit=limit, offset=offset)

        roles = {member.user_id: ClubRole(member.role) for member in members}
        summaries = await self.user_repository.get_summaries_by_ids(list(roles))

        page = Page(
            items=[
                ClubMemberResponse(
                    **summary.model_dump(),
                    role=ClubRole.owner if summary.id == club.owner_id else roles[summary.id],
                )
                for summary in summaries
            ],
            total=club.members_count,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def delete_book_club(self, owner: Principal, book_club_id: int) -> ResponseModel:
        club = await self.book_club_repository.get_book_club(book_club_id)
        require_permission(owner, club.owner_id, message="Пользователь не является владельцем книжного клуба")

        # Треды клуба уносит каскад БД (threads.club_id ON DELETE CASCADE) в той же
        # транзакции.
        cover_key = await self.book_club_repository.delete_book_club(club)
        # Обложка живёт вне БД, каскад её не уносит.
        await media.delete_image(cover_key)

        return ResponseModel.ok(message="Книжный клуб успешно удален")

    async def join(self, user: Principal, club_id: int) -> ResponseModel[BookClubResponse]:
        club = await self.book_club_repository.get_book_club(club_id)

        if club.privacy != ClubPrivacy.public.value:
            raise Forbidden(_CLOSED_CLUB_MESSAGES[club.privacy])

        db_club: BookClub = await self.book_club_repository.add_member(club_id, user.id)

        return ResponseModel.ok(await self._to_response(db_club))

    async def leave(self, user: Principal, club_id: int) -> ResponseModel[BookClubResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        # Тот же запрет, что и на исключение владельца: иначе клубом правил бы
        # тот, кого нет в составе, а роль владельца выводится из владения и
        # осталась бы при нём.
        if club.owner_id is not None and user.id == club.owner_id:
            raise Forbidden(_OWNER_STAYS_MESSAGE)

        db_club: BookClub = await self.book_club_repository.remove_member(club_id, user.id)

        return ResponseModel.ok(await self._to_response(db_club))

    # Роль пользователя в клубе, либо None - он не участник. Владелец в
    # club_members.role не хранится, его роль выводится из owner_id клуба.
    async def _role_of(self, club: BookClub, user_id: int) -> Optional[ClubRole]:
        if club.owner_id is not None and user_id == club.owner_id:
            return ClubRole.owner

        role = await self.book_club_repository.get_role(club.id, user_id)

        return ClubRole(role) if role is not None else None

    async def _require_manager(self, club: BookClub, user: Principal, message: str) -> ClubRole:
        """Пропускает владельца, модератора и админа; возвращает роль действующего."""
        if user.is_admin:
            return ClubRole.owner

        role = await self._role_of(club, user.id)
        if role not in (ClubRole.owner, ClubRole.moderator):
            raise Forbidden(message)

        return role

    async def create_invite(
        self, user: Principal, club_id: int, model: CreateInviteRequest
    ) -> ResponseModel[InviteResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        await self._require_manager(club, user, "Создавать приглашения может владелец или модератор клуба")

        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=model.expires_in_days)
            if model.expires_in_days is not None
            else None
        )
        invite = await self.book_club_repository.create_invite(club_id, user.id, expires_at)

        return ResponseModel.ok(InviteResponse.model_validate(invite))

    async def join_by_invite(
        self, user: Principal, model: JoinByInviteRequest
    ) -> ResponseModel[BookClubResponse]:
        invite = await self.book_club_repository.get_invite(model.code)

        if invite.expires_at is not None and invite.expires_at <= datetime.now(timezone.utc):
            raise Forbidden("Срок действия приглашения истёк")

        # Приглашение - и есть разрешение войти: режим приватности клуба тут не
        # проверяется, иначе код был бы бесполезен именно там, где он нужен.
        db_club: BookClub = await self.book_club_repository.add_member(invite.club_id, user.id)

        return ResponseModel.ok(await self._to_response(db_club))

    async def request_join(self, user: Principal, club_id: int) -> ResponseModel[JoinRequestResponse]:
        club = await self.book_club_repository.get_book_club(club_id)

        if club.privacy != ClubPrivacy.by_request.value:
            raise Conflict(errors=["Этот клуб не принимает заявки на вступление"])

        if await self.book_club_repository.is_member(club_id, user.id):
            raise Conflict(errors=["Пользователь уже является участником клуба"])

        join_request = await self.book_club_repository.upsert_join_request(club_id, user.id)

        return ResponseModel.ok((await self._to_request_responses([join_request]))[0])

    async def get_join_requests(
        self, user: Principal, club_id: int, limit: int, offset: int
    ) -> ResponseModel[Page[JoinRequestResponse]]:
        club = await self.book_club_repository.get_book_club(club_id)
        await self._require_manager(club, user, "Смотреть заявки может владелец или модератор клуба")

        requests, total = await self.book_club_repository.get_pending_join_requests(
            club_id, limit=limit, offset=offset
        )

        page = Page(
            items=await self._to_request_responses(requests),
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    # Заявители - из iam, поэтому подтягиваем их батчем на всю страницу, как
    # владельцев клубов.
    async def _to_request_responses(self, requests: List[ClubJoinRequest]) -> List[JoinRequestResponse]:
        summaries = await self.user_repository.get_summaries_by_ids(
            list({request.user_id for request in requests})
        )
        users = {summary.id: summary for summary in summaries}

        return [
            JoinRequestResponse(
                id=request.id,
                club_id=request.club_id,
                user=users.get(request.user_id),
                status=JoinRequestStatus(request.status),
                created_at=request.created_at,
            )
            for request in requests
        ]

    async def resolve_join_request(
        self, user: Principal, club_id: int, request_id: int, status: JoinRequestStatus
    ) -> ResponseModel[JoinRequestResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        await self._require_manager(club, user, "Рассматривать заявки может владелец или модератор клуба")

        join_request = await self.book_club_repository.get_join_request(request_id)
        # Заявка адресуется парой (клуб, id): чужой id из другого клуба - не «нет
        # прав», а несуществующая в этом клубе заявка.
        if join_request.club_id != club_id:
            raise NotFound("Заявка с таким id не найдена")

        join_request = await self.book_club_repository.resolve_join_request(join_request, status)

        # Заявитель мог войти по приглашению, пока заявка ждала решения - тогда
        # повторное добавление упало бы конфликтом и откатило рассмотрение.
        if status is JoinRequestStatus.approved and not await self.book_club_repository.is_member(
            club_id, join_request.user_id
        ):
            await self.book_club_repository.add_member(club_id, join_request.user_id)

        return ResponseModel.ok((await self._to_request_responses([join_request]))[0])

    async def set_member_role(
        self, user: Principal, club_id: int, user_id: int, model: UpdateMemberRoleRequest
    ) -> ResponseModel:
        club = await self.book_club_repository.get_book_club(club_id)
        # Модератора назначает только владелец: иначе модератор наплодит себе равных.
        require_permission(user, club.owner_id, message="Назначать роли может только владелец клуба")

        if user_id == club.owner_id:
            raise UnprocessableEntity(
                message="Роль владельца меняется передачей клуба",
                errors=["field: user_id, message: это владелец клуба"],
            )

        await self.book_club_repository.set_role(club_id, user_id, model.role.value)

        return ResponseModel.ok(message="Роль участника обновлена")

    async def remove_member(self, user: Principal, club_id: int, user_id: int) -> ResponseModel[BookClubResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        actor_role = await self._require_manager(
            club, user, "Исключать участников может владелец или модератор клуба"
        )
        target_role = await self._role_of(club, user_id)

        if target_role is ClubRole.owner:
            raise Forbidden(_OWNER_STAYS_MESSAGE)

        if actor_role is ClubRole.moderator and target_role is ClubRole.moderator:
            raise Forbidden("Модератор не может исключить другого модератора")

        db_club: BookClub = await self.book_club_repository.remove_member(club_id, user_id)

        return ResponseModel.ok(await self._to_response(db_club))

    async def transfer_ownership(
        self, user: Principal, club_id: int, model: TransferOwnershipRequest
    ) -> ResponseModel[BookClubResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        require_permission(user, club.owner_id, message="Передавать клуб может только его владелец")

        db_club: BookClub = await self.book_club_repository.transfer_ownership(club, model.user_id)

        return ResponseModel.ok(await self._to_response(db_club))


class ReadingService:
    reading_repository: ReadingRepository
    book_club_repository: BookClubRepository
    book_service: BookService
    user_repository: UserRepository

    def __init__(
        self,
        reading_repository: ReadingRepository,
        book_club_repository: BookClubRepository,
        book_service: BookService,
        user_repository: UserRepository,
    ) -> None:
        self.reading_repository = reading_repository
        self.book_club_repository = book_club_repository
        self.book_service = book_service
        self.user_repository = user_repository

    async def _to_responses(self, readings: List[Reading]) -> List[ReadingResponse]:
        return await _reading_responses(self.reading_repository, readings)

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


# Потолок кандидатов в клубе. Список номинаций отдаётся целиком, без страниц:
# голосование живёт до закрытия, и потолок держит его в размере, который не жалко
# получить одним ответом, а заодно не даёт одному участнику завалить экран клуба.
# ponytail: общий потолок на клуб, персональной квоты нет - появится, если начнут
# спамить в пределах полусотни.
MAX_NOMINATIONS_PER_CLUB = 50


class NominationService:
    """Голосование за следующую книгу клуба: номинации, голоса, закрытие."""

    nomination_repository: NominationRepository
    reading_repository: ReadingRepository
    book_club_repository: BookClubRepository
    book_service: BookService

    def __init__(
        self,
        nomination_repository: NominationRepository,
        reading_repository: ReadingRepository,
        book_club_repository: BookClubRepository,
        book_service: BookService,
    ) -> None:
        self.nomination_repository = nomination_repository
        self.reading_repository = reading_repository
        self.book_club_repository = book_club_repository
        self.book_service = book_service

    async def _require_member(self, club_id: int, user: Principal, action: str) -> None:
        if not await self.book_club_repository.is_member(club_id, user.id):
            raise Forbidden(errors=[f"{action} могут только участники клуба"])

    # Голоса не хранятся счётчиком в номинации: их считает один запрос на весь
    # клуб, а голосование живёт до закрытия - расходиться нечему.
    async def _to_responses(
        self, club_id: int, nominations: List[BookNomination], user: Principal
    ) -> List[NominationResponse]:
        votes = await self.nomination_repository.count_votes(club_id)
        my_vote = await self.nomination_repository.get_vote(club_id, user.id)

        return [
            NominationResponse(
                id=nomination.id,
                club_id=nomination.club_id,
                book=BookResponse.model_validate(nomination.book) if nomination.book else None,
                votes_count=votes.get(nomination.id, 0),
                voted=my_vote is not None and my_vote.nomination_id == nomination.id,
            )
            for nomination in nominations
        ]

    async def nominate(
        self, user: Principal, club_id: int, model: CreateNominationRequest
    ) -> ResponseModel[NominationResponse]:
        await self.book_club_repository.get_book_club(club_id)
        await self._require_member(club_id, user, "Номинировать книги")

        # Потолок - защита от заваленного списка, а не инвариант: две параллельные
        # номинации на границе могут дать 51-ю, и это не страшно.
        if await self.nomination_repository.count_nominations(club_id) >= MAX_NOMINATIONS_PER_CLUB:
            raise Conflict(
                errors=[
                    f"В клубе уже {MAX_NOMINATIONS_PER_CLUB} книг-кандидатов - "
                    f"закройте голосование, чтобы начать новое"
                ]
            )

        book = await self.book_service.get_or_create_book(model.book_volume_id)
        nomination = await self.nomination_repository.create_nomination(club_id, book.id)

        return ResponseModel.ok((await self._to_responses(club_id, [nomination], user))[0])

    async def get_nominations(
        self, user: Principal, club_id: int
    ) -> ResponseModel[List[NominationResponse]]:
        await self.book_club_repository.get_book_club(club_id)
        nominations = await self.nomination_repository.get_nominations(club_id)

        return ResponseModel.ok(await self._to_responses(club_id, nominations, user))

    async def vote(self, user: Principal, nomination_id: int) -> ResponseModel[NominationResponse]:
        nomination = await self.nomination_repository.get_nomination(nomination_id)
        await self._require_member(nomination.club_id, user, "Голосовать")

        await self.nomination_repository.set_vote(nomination.club_id, user.id, nomination_id)

        return ResponseModel.ok(
            (await self._to_responses(nomination.club_id, [nomination], user))[0]
        )

    async def unvote(self, user: Principal, nomination_id: int) -> ResponseModel[NominationResponse]:
        nomination = await self.nomination_repository.get_nomination(nomination_id)

        if not await self.nomination_repository.delete_vote(
            nomination.club_id, user.id, nomination_id
        ):
            raise Conflict(errors=["Вы не голосовали за эту номинацию"])

        return ResponseModel.ok(
            (await self._to_responses(nomination.club_id, [nomination], user))[0]
        )

    async def close_voting(
        self, owner: Principal, club_id: int, model: ReadingScheduleRequest
    ) -> ResponseModel[ReadingResponse]:
        club = await self.book_club_repository.get_book_club(club_id)
        require_permission(owner, club.owner_id, message="Закрывать голосование может только владелец клуба")

        nominations = await self.nomination_repository.get_nominations(club_id)
        if not nominations:
            raise Conflict(errors=["В клубе нет ни одной номинации"])

        votes = await self.nomination_repository.count_votes(club_id)
        # Больше голосов, при равенстве - кто номинирован раньше (меньший id).
        winner = max(nominations, key=lambda nomination: (votes.get(nomination.id, 0), -nomination.id))

        # Сначала заход: если у клуба уже есть незакрытый, создание упадёт
        # Conflict-ом и номинации останутся на месте вместе с голосами.
        reading = await self.reading_repository.create_reading(club_id, winner.book_id, model)
        await self.nomination_repository.clear_nominations(club_id)

        return ResponseModel.ok((await _reading_responses(self.reading_repository, [reading]))[0])
