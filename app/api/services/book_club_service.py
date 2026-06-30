from typing import List

from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel

from app.db.models.db_user import DBUser
from app.db.models.db_book_club import DBBookClub

from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.user_repository import UserRepository

from app.schemas.book_club_schema import CreateBookClubRequestModel, BookClubResponseModel
from app.schemas.public_user_schema import UserSummaryModel


class BookClubService:
    user_repository: UserRepository
    book_club_repository: BookClubRepository

    def __init__(self, user_repository: UserRepository, book_club_repository: BookClubRepository) -> None:
        self.user_repository = user_repository
        self.book_club_repository = book_club_repository

    async def create_book_club(self, model: CreateBookClubRequestModel, owner: DBUser) -> ResponseModel[BookClubResponseModel]:
        db_book_club: DBBookClub = await self.book_club_repository.create_book_club(owner, model)

        return ResponseModel.ok(BookClubResponseModel.model_validate(db_book_club))

    async def get_book_clubs(self) -> ResponseModel[List[BookClubResponseModel]]:
        db_clubs: List[DBBookClub] = await self.book_club_repository.get_book_clubs()
        clubs = [BookClubResponseModel.model_validate(club) for club in db_clubs]

        return ResponseModel.ok(clubs)

    async def get_book_club(self, club_id: int) -> ResponseModel[BookClubResponseModel]:
        db_club: DBBookClub = await self.book_club_repository.get_book_club(club_id)

        return ResponseModel.ok(BookClubResponseModel.model_validate(db_club))

    async def get_owned_book_clubs(self, owner: DBUser) -> ResponseModel[List[BookClubResponseModel]]:
        db_clubs: List[DBBookClub] = await self.book_club_repository.get_owned_book_clubs(owner)
        clubs = [BookClubResponseModel.model_validate(club) for club in db_clubs]

        return ResponseModel.ok(clubs)

    async def get_members(self, club_id: int, limit: int, offset: int) -> ResponseModel[Page[UserSummaryModel]]:
        await self.book_club_repository.get_book_club(club_id)
        users, total = await self.book_club_repository.get_members(club_id, limit=limit, offset=offset)

        page = Page(
            items=[UserSummaryModel.model_validate(user) for user in users],
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def delete_book_club(self, owner: DBUser, book_club_id: int) -> ResponseModel:
        await self.book_club_repository.delete_book_club(owner, book_club_id)

        return ResponseModel.ok(message="Книжный клуб успешно удален")

    async def join(self, user: DBUser, club_id: int) -> ResponseModel[BookClubResponseModel]:
        db_club: DBBookClub = await self.book_club_repository.join_book_club(user=user, club_id=club_id)
        club = BookClubResponseModel.model_validate(db_club)

        return ResponseModel.ok(club)


    async def leave(self, user: DBUser, club_id: int) -> ResponseModel[BookClubResponseModel]:
        db_club: DBBookClub = await self.book_club_repository.remove_member(user, club_id)
        club = BookClubResponseModel.model_validate(db_club)

        return ResponseModel.ok(club)