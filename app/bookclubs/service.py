from typing import List

from app.bookclubs.models import BookClub, Genre
from app.bookclubs.repository import BookClubRepository, GenreRepository
from app.bookclubs.schemas import (
    CreateBookClubRequest,
    UpdateBookClubGenresRequest,
    SearchBookClubsRequest,
    BookClubResponse,
    GenreResponse,
)
from app.core.errors.errors import UnprocessableEntity
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.iam.models import User
from app.iam.schemas import UserSummary


class BookClubService:
    book_club_repository: BookClubRepository
    genre_repository: GenreRepository

    def __init__(
        self,
        book_club_repository: BookClubRepository,
        genre_repository: GenreRepository,
    ) -> None:
        self.book_club_repository = book_club_repository
        self.genre_repository = genre_repository

    async def create_book_club(self, model: CreateBookClubRequest, owner: User) -> ResponseModel[BookClubResponse]:
        genres = await self._resolve_genres(model.genres)

        db_book_club: BookClub = await self.book_club_repository.create_book_club(
            owner, model, [genre.id for genre in genres]
        )

        return ResponseModel.ok(BookClubResponse.model_validate(db_book_club))

    async def set_genres(
        self, owner: User, club_id: int, model: UpdateBookClubGenresRequest
    ) -> ResponseModel[BookClubResponse]:
        genres = await self._resolve_genres(model.genres)

        db_book_club: BookClub = await self.book_club_repository.set_genres(owner, club_id, genres)

        return ResponseModel.ok(BookClubResponse.model_validate(db_book_club))

    async def _resolve_genres(self, codes: List[str]) -> List[Genre]:
        unique_codes = list(dict.fromkeys(codes))
        genres: List[Genre] = await self.genre_repository.get_active_by_codes(unique_codes)

        found = {genre.code for genre in genres}
        missing = [code for code in unique_codes if code not in found]
        if missing:
            raise UnprocessableEntity(
                message="Неизвестный жанр",
                errors=[f"field: genres, message: неизвестный жанр {code}" for code in missing],
            )

        return genres

    async def list_genres(self) -> ResponseModel[List[GenreResponse]]:
        genres: List[Genre] = await self.genre_repository.list_active()

        return ResponseModel.ok([GenreResponse.model_validate(genre) for genre in genres])

    async def get_book_clubs(self, limit: int, offset: int) -> ResponseModel[Page[BookClubResponse]]:
        db_clubs, total = await self.book_club_repository.get_book_clubs(limit, offset)

        return self._page(db_clubs, total, limit, offset)

    async def search_book_clubs(
        self, user: User, model: SearchBookClubsRequest
    ) -> ResponseModel[Page[BookClubResponse]]:
        db_clubs, total = await self.book_club_repository.get_book_clubs(
            model.limit, model.offset, user, model.relation, model.query
        )

        return self._page(db_clubs, total, model.limit, model.offset)

    @staticmethod
    def _page(db_clubs: List[BookClub], total: int, limit: int, offset: int) -> ResponseModel[Page[BookClubResponse]]:
        page = Page(
            items=[BookClubResponse.model_validate(club) for club in db_clubs],
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def get_book_club(self, club_id: int) -> ResponseModel[BookClubResponse]:
        db_club: BookClub = await self.book_club_repository.get_book_club(club_id)

        return ResponseModel.ok(BookClubResponse.model_validate(db_club))

    async def get_members(self, club_id: int, limit: int, offset: int) -> ResponseModel[Page[UserSummary]]:
        await self.book_club_repository.get_book_club(club_id)
        users, total = await self.book_club_repository.get_members(club_id, limit=limit, offset=offset)

        page = Page(
            items=[UserSummary.model_validate(user) for user in users],
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def delete_book_club(self, owner: User, book_club_id: int) -> ResponseModel:
        await self.book_club_repository.delete_book_club(owner, book_club_id)

        return ResponseModel.ok(message="Книжный клуб успешно удален")

    async def join(self, user: User, club_id: int) -> ResponseModel[BookClubResponse]:
        db_club: BookClub = await self.book_club_repository.join_book_club(user=user, club_id=club_id)
        club = BookClubResponse.model_validate(db_club)

        return ResponseModel.ok(club)


    async def leave(self, user: User, club_id: int) -> ResponseModel[BookClubResponse]:
        db_club: BookClub = await self.book_club_repository.remove_member(user, club_id)
        club = BookClubResponse.model_validate(db_club)

        return ResponseModel.ok(club)
