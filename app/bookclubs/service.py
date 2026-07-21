from typing import List

from app.bookclubs.models import BookClub
from app.bookclubs.repository import BookClubRepository
from app.bookclubs.schemas import (
    CreateBookClubRequest,
    UpdateBookClubGenresRequest,
    SearchBookClubsRequest,
    BookClubResponse,
)
from app.bookclubs.ports import GenresPort, UsersPort
from app.core import events
from app.core.contracts import GenreResponse, Principal, UserSummary
from app.core.errors.errors import UnprocessableEntity
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel


class BookClubService:
    book_club_repository: BookClubRepository
    genre_repository: GenresPort
    user_repository: UsersPort

    def __init__(
        self,
        book_club_repository: BookClubRepository,
        genre_repository: GenresPort,
        user_repository: UsersPort,
    ) -> None:
        self.book_club_repository = book_club_repository
        self.genre_repository = genre_repository
        self.user_repository = user_repository

    # owner и genres больше не живут в модели - клуб хранит только id, подтягиваем
    # их батчем из iam/genres (после распила - вызовы соседних сервисов), одним
    # запросом на всю страницу вместо N+1. threads_count - денормализованный
    # столбец, который ведёт домен клубов по событиям тредов (см. events.py).
    async def _to_responses(self, clubs: List[BookClub]) -> List[BookClubResponse]:
        owners = await self._owners_by_id(clubs)
        genres_by_club = await self._genres_by_club(clubs)

        responses = []
        for club in clubs:
            response = BookClubResponse.model_validate(club)
            response.owner = owners.get(club.owner_id)
            response.genres = genres_by_club.get(club.id, [])
            responses.append(response)

        return responses

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
            genres_by_club[club_id] = [
                GenreResponse.model_validate(genre) for genre in genres if genre.id in club_genre_ids
            ]

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
        # id жанров, подходящих под поисковый запрос, берём у genres -
        # после распила это вызов сервиса жанров
        term = (model.query or "").strip()
        genre_ids = await self.genre_repository.search_ids(term) if term else []

        db_clubs, total = await self.book_club_repository.get_book_clubs(
            model.limit, model.offset, user, model.relation, model.query, genre_ids
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
        await self.book_club_repository.get_book_club(club_id)
        user_ids, total = await self.book_club_repository.get_members(club_id, limit=limit, offset=offset)

        page = Page(
            items=await self.user_repository.get_summaries_by_ids(user_ids),
            total=total,
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
