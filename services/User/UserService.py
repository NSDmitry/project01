from fastapi import HTTPException
from sqlalchemy.orm import Session

from DBmodels import DBUser
from services.OAuth2PasswordBearer.OAuth2PasswordBearer import get_current_user
from services.User.Models import PublicUserResponseModel


class UserSerivce:
    @classmethod
    def get_current_user(cls, access_token: str, db: Session) -> PublicUserResponseModel:
        db_user: DBUser = get_current_user(access_token, db)

        return PublicUserResponseModel.from_db_model(db_model=db_user)

    @classmethod
    def get_user_by_id(cls, user_id: int, db: Session) -> PublicUserResponseModel:
        db_user: DBUser = db.query(DBUser).filter(DBUser.id == user_id).first()

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким id не найден")

        return PublicUserResponseModel.from_db_model(db_model=db_user)