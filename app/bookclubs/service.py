from typing import List

from app.bookclubs.models import BookClub
from app.bookclubs.repository import BookClubRepository
from app.bookclubs.schemas import CreateBookClubRequest, BookClubResponse, BookClubRelation
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.iam.models import User
from app.iam.repository import UserRepository
from app.iam.schemas import UserSummary


class BookClubService:
    user_repository: UserRepository
    book_club_repository: BookClubRepository

    def __init__(self, user_repository: UserRepository, book_club_repository: BookClubRepository) -> None:
        self.user_repository = user_repository
        self.book_club_repository = book_club_repository

    async def create_book_club(self, model: CreateBookClubRequest, owner: User) -> ResponseModel[BookClubResponse]:
        db_book_club: BookClub = await self.book_club_repository.create_book_club(owner, model)

        return ResponseModel.ok(BookClubResponse.model_validate(db_book_club))

    async def get_book_clubs(self, user: User, relation: BookClubRelation | None = None) -> ResponseModel[List[BookClubResponse]]:
        db_clubs: List[BookClub] = await self.book_club_repository.get_book_clubs(user, relation)
        clubs = [BookClubResponse.model_validate(club) for club in db_clubs]

        return ResponseModel.ok(clubs)

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
