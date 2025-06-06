from typing import List

from app.core.errors.errors import Conflict
from app.core.models.response_model import ResponseModel

from app.db.models.db_user import DBUser
from app.db.models.db_book_club import DBBookClub

from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.user_repository import UserRepository

from app.schemas.book_club_schema import CreateBookClubRequestModel, BookClubResponseModel


class BookClubSerivce:
    user_repository: UserRepository
    book_club_repository: BookClubRepository

    def __init__(self) -> None:
        self.user_repository = UserRepository()
        self.book_club_repository = BookClubRepository()

    def create_book_club(self, model: CreateBookClubRequestModel, access_token: str) -> ResponseModel[BookClubResponseModel]:
        self.__validate_create_book_club_request(model)

        owner: DBUser = self.user_repository.get_user_by_access_token(access_token)
        db_book_club: DBBookClub = self.book_club_repository.create_book_blub(owner, model)

        return ResponseModel.success_response(BookClubResponseModel(**db_book_club.to_dict()))

    def get_book_clubs(self) -> ResponseModel[List[BookClubResponseModel]]:
        db_clubs: List[DBBookClub] = self.book_club_repository.get_book_clubs()
        clubs = [BookClubResponseModel(**club.to_dict()) for club in db_clubs]

        return ResponseModel.success_response(clubs)

    def get_book_club(self, club_id: int) -> ResponseModel[BookClubResponseModel]:
        db_club: DBBookClub = self.book_club_repository.get_book_club(club_id)

        return ResponseModel.success_response(BookClubResponseModel(**db_club.to_dict()))

    def get_owned_book_clubs(self, access_token: str) -> ResponseModel[List[BookClubResponseModel]]:
        owner: DBUser = self.user_repository.get_user_by_access_token(access_token)
        db_clubs: List[DBBookClub] = self.book_club_repository.get_owned_book_blubs(owner)
        clubs = [BookClubResponseModel(**club.to_dict()) for club in db_clubs]

        return ResponseModel.success_response(clubs)

    def delete_book_club(self, access_token: str, book_club_id: int) -> ResponseModel:
        owner: DBUser = self.user_repository.get_user_by_access_token(access_token)
        self.book_club_repository.delete_book_club(owner, book_club_id)

        return ResponseModel.success_response(message="Книжный клуб успешно удален")

    def join(self, access_token: str, club_id: int) -> ResponseModel[BookClubResponseModel]:
        user: DBUser = self.user_repository.get_user_by_access_token(access_token)
        db_club: DBBookClub = self.book_club_repository.join_book_club(user=user, club_id=club_id)
        club = BookClubResponseModel(**db_club.to_dict())

        return ResponseModel.success_response(club)


    def leave(self, access_token: str, club_id: int) -> ResponseModel[BookClubResponseModel]:
        user: DBUser = self.user_repository.get_user_by_access_token(access_token)
        db_club: DBBookClub = self.book_club_repository.remove_member(user, club_id)
        club = BookClubResponseModel(**db_club.to_dict())

        return ResponseModel.success_response(club)

    def __validate_create_book_club_request(self, model: CreateBookClubRequestModel):
        bookclubs: DBBookClub = self.book_club_repository.get_book_clubs()

        if model.name in [club.name for club in bookclubs]:
            raise Conflict(
                message="Клуб с таким названием уже существует",
                errors=["field: name, message: Это имя уже используется "]
            )

        if not model.name:
            raise Conflict(
                message="Имя книжного клуба не может быть пустым.",
                errors=["field: name, message: Имя книжного клуба не может быть пустым."])

        if not model.description:
            raise Conflict(
                message="Описание книжного клуба не может быть пустым.",
                errors=["field: description, message: Описание книжного клуба не может быть пустым."])

        if len(model.name) < 3 or len(model.name) > 100:
            raise Conflict(
                message="Название книжного клуба должно быть от 3 до 100 символов.",
                errors=["field: name, message: Название книжного клуба должно быть от 3 до 100 символов."]
            )

        if len(model.description) < 3 or len(model.description) > 500:
            raise Conflict(
                message="Описание книжного клуба должно быть от 3 до 500 символов.",
                errors=["field: description, message: Описание книжного клуба должно быть от 3 до 500 символов."]
            )