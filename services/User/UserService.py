from fastapi import HTTPException
from sqlalchemy.orm import Session

from DBmodels import DBUser
from Repositories.UserRepository import UserRepository
from services.User.Models import PublicUserResponseModel, UpdateUserRequestModel


class UserSerivce:
    @classmethod
    def get_current_user(cls, access_token: str, db: Session) -> PublicUserResponseModel:
        db_user: DBUser = UserRepository.get_user_by_access_token(access_token, db)

        return PublicUserResponseModel.from_db_model(db_model=db_user)

    @classmethod
    def get_user_by_id(cls, user_id: int, db: Session) -> PublicUserResponseModel:
        db_user: DBUser = UserRepository.get_user_by_id(user_id, db)

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким id не найден")

        return PublicUserResponseModel.from_db_model(db_model=db_user)

    @classmethod
    def update_user_info(cls, access_token: str, model: UpdateUserRequestModel, db: Session) -> PublicUserResponseModel:
        db_user: DBUser = UserRepository.update_user_info(access_token, model.name, model.phone_number, db)

        return PublicUserResponseModel.from_db_model(db_user)