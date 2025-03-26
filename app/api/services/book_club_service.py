from typing import List

from app.db.models.db_user import DBUser
from app.db.models.db_book_club import DBBookClub

from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.user_repository import UserRepository

from app.schemas.book_club_schema import CreateBookClubRequestModel, BookClubResponseModel, DeleteBookClubResponse


class BookClubSerivce:
    user_repository: UserRepository
    book_club_repository: BookClubRepository

    def __init__(self) -> None:
        self.user_repository = UserRepository()
        self.book_club_repository = BookClubRepository()

    def create_book_club(self, model: CreateBookClubRequestModel, access_token: str) -> BookClubResponseModel:
        owner: DBUser = self.user_repository.get_user_by_access_token(access_token)
        db_book_club: DBBookClub = self.book_club_repository.create_book_blub(owner, model)

        return BookClubResponseModel.from_db_model(db_book_club)

    def get_book_clubs(self) -> List[BookClubResponseModel]:
        db_clubs: List[DBBookClub] = self.book_club_repository.get_book_clubs()

        return [BookClubResponseModel.from_db_model(club) for club in db_clubs]

    def get_owned_book_clubs(self, access_token: str) -> List[BookClubResponseModel]:
        owner: DBUser = self.user_repository.get_user_by_access_token(access_token)
        clubs: List[DBBookClub] = self.book_club_repository.get_owned_book_blubs(owner)

        return [BookClubResponseModel.from_db_model(club) for club in clubs]

    def delete_book_club(self, access_token: str, book_club_id: int) -> DeleteBookClubResponse:
        owner: DBUser = self.user_repository.get_user_by_access_token(access_token)
        self.book_club_repository.delete_book_club(owner, book_club_id)

        return DeleteBookClubResponse(message="Книжный клуб успешно удален")

    def join(self, access_token: str, club_id: int) -> BookClubResponseModel:
        user: DBUser = self.user_repository.get_user_by_access_token(access_token)
        club: DBBookClub = self.book_club_repository.join_book_club(user=user, club_id=club_id)

        return BookClubResponseModel.from_db_model(club)

    def leave(self, access_token: str, club_id: int) -> BookClubResponseModel:
        user: DBUser = self.user_repository.get_user_by_access_token(access_token)
        club: DBBookClub = self.book_club_repository.remove_member(user, club_id)

        return BookClubResponseModel.from_db_model(club)