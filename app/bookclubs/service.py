from typing import List

from app.bookclubs.models import BookClub
from app.bookclubs.repository import BookClubRepository
from app.bookclubs.schemas import (
    CreateBookClubRequest,
    UpdateBookClubGenresRequest,
    SearchBookClubsRequest,
    BookClubResponse,
)
from app.core import events
from app.core.errors.errors import UnprocessableEntity
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.genres.models import Genre
from app.genres.repository import GenreRepository
from app.iam.models import User
from app.iam.repository import UserRepository
from app.iam.schemas import UserSummary
from app.threads.repository import ThreadRepository


class BookClubService:
    book_club_repository: BookClubRepository
    genre_repository: GenreRepository
    user_repository: UserRepository
    thread_repository: ThreadRepository

    def __init__(
            self,
            book_club_repository: BookClubRepository,
            genre_repository: GenreRepository,
            user_repository: UserRepository,
            thread_repository: ThreadRepository,
    ) -> None:
        self.book_club_repository = book_club_repository
        self.genre_repository = genre_repository
        self.user_repository = user_repository
        self.thread_repository = thread_repository

    # owner и threads_count больше не живут в модели - клуб хранит только id.
    # UserSummary и счётчик тредов подтягиваем батчем из iam/threads
    # (после распила - вызовы соседних сервисов).
    async def _to_responses(self, clubs: List[BookClub]) -> List[BookClubResponse]:
        owner_ids = {club.owner_id for club in clubs if club.owner_id is not None}
        owners = {}
        if owner_ids:
            summaries = await self.user_repository.get_summaries_by_ids(list(owner_ids))
            owners = {summary.id: summary for summary in summaries}

        threads_counts = await self.thread_repository.get_threads_counts(
            [club.id for club in clubs]
        )

        responses = []
        for club in clubs:
            response = BookClubResponse.model_validate(club)
            response.owner = owners.get(club.owner_id)
            response.threads_count = threads_counts.get(club.id, 0)
            responses.append(response)

        return responses

    async def _to_response(self, club: BookClub) -> BookClubResponse:
        return (await self._to_responses([club]))[0]

    async def create_book_club(self, model: CreateBookClubRequest, owner: User) -> ResponseModel[BookClubResponse]:
        genres = await self._resolve_genres(model.genres)

        db_book_club: BookClub = await self.book_club_repository.create_book_club(
            owner, model, [genre.id for genre in genres]
        )

        return ResponseModel.ok(await self._to_response(db_book_club))

    async def set_genres(
            self, owner: User, club_id: int, model: UpdateBookClubGenresRequest
    ) -> ResponseModel[BookClubResponse]:
        genres = await self._resolve_genres(model.genres)

        db_book_club: BookClub = await self.book_club_repository.set_genres(owner, club_id, genres)

        return ResponseModel.ok(await self._to_response(db_book_club))

    async def _resolve_genres(self, codes: List[str]) -> List[Genre]:
        unique_codes = list(dict.fromkeys(codes))
        genres: List[Genre] = await self.genre_repository.get_by_codes(unique_codes)

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
            self, user: User, model: SearchBookClubsRequest
    ) -> ResponseModel[Page[BookClubResponse]]:
        db_clubs, total = await self.book_club_repository.get_book_clubs(
            model.limit, model.offset, user, model.relation, model.query
        )

        return await self._page(db_clubs, total, model.limit, model.offset)

    async def _page(self, db_clubs: List[BookClub], total: int, limit: int, offset: int) -> ResponseModel[
        Page[BookClubResponse]]:
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

    async def delete_book_club(self, owner: User, book_club_id: int) -> ResponseModel:
        await self.book_club_repository.delete_book_club(owner, book_club_id)
        # FK threads.club_id больше нет - треды удалённого клуба чистит
        # threads по событию
        await events.publish(events.CLUBS_DELETED, {"club_ids": [book_club_id]})

        return ResponseModel.ok(message="Книжный клуб успешно удален")

    async def join(self, user: User, club_id: int) -> ResponseModel[BookClubResponse]:
        db_club: BookClub = await self.book_club_repository.join_book_club(user=user, club_id=club_id)
        club = await self._to_response(db_club)

        return ResponseModel.ok(club)

    async def leave(self, user: User, club_id: int) -> ResponseModel[BookClubResponse]:
        db_club: BookClub = await self.book_club_repository.remove_member(user, club_id)
        club = await self._to_response(db_club)

        return ResponseModel.ok(club)
