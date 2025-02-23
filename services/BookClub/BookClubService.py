from fastapi import Depends
from sqlalchemy.orm import Session

from DBmodels import DBUser, DBBookClub
from database import get_db
from repositories.BookClubRepository import BookClubRepository
from services.BookClub.Models import CreateBookClubRequestModel, BookClubResponseModel
from services.User.Models import PublicUserResponseModel
from services.User.UserService import UserSerivce


class BookClubSerivce:
    @classmethod
    def create_book_club(cls, model: CreateBookClubRequestModel, access_token: str, db: Session = Depends(get_db)) -> BookClubResponseModel:
        db_club_creator: DBUser = UserSerivce.get_current_user(access_token, db)
        db_book_club: DBBookClub = BookClubRepository.create_book_blub(db_club_creator, model, db)

        return BookClubResponseModel.from_db_model(db_book_club)