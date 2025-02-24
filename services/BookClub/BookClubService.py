from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session

from DBmodels import DBUser, DBBookClub
from database import get_db
from repositories.BookClubRepository import BookClubRepository
from repositories.UserRepository import UserRepository
from services.BookClub.Models import CreateBookClubRequestModel, BookClubResponseModel, DeleteBookClubResponse
from services.User.Models import PublicUserResponseModel
from services.User.UserService import UserSerivce


class BookClubSerivce:
    @classmethod
    def create_book_club(cls, model: CreateBookClubRequestModel, access_token: str, db: Session = Depends(get_db)) -> BookClubResponseModel:
        owner: DBUser = UserRepository.get_user_by_access_token(access_token, db)
        db_book_club: DBBookClub = BookClubRepository.create_book_blub(owner, model, db)

        return BookClubResponseModel.from_db_model(db_book_club)

    @classmethod
    def get_owned_book_clubs(cls, access_token: str, db: Session = Depends(get_db())) -> List[BookClubResponseModel]:
        owner: DBUser = UserRepository.get_user_by_access_token(access_token, db)
        clubs = BookClubRepository.get_owned_book_blubs(owner, db)

        return [BookClubResponseModel.from_db_model(club) for club in clubs]

    @classmethod
    def delete_book_club(cls, access_token: str, book_club_id: int, db: Session = Depends(get_db())) -> DeleteBookClubResponse:
        owner: DBUser = UserRepository.get_user_by_access_token(access_token, db)
        BookClubRepository.delete_book_club(owner, book_club_id, db)

        return DeleteBookClubResponse(message="Книжный клуб успешно удален")