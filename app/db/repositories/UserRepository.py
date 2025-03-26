import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.OAuth2PasswordBearer import get_current_user
from app.db.models.DBUser import DBUser


class UserRepository:
    db: Session

    logger = logging.getLogger(__name__)

    def __init__(self, db: Session = get_db()) -> None:
        self.db = db

    def get_user_by_access_token(self, access_token: str) -> DBUser:
        return get_current_user(access_token)

    def get_user_by_id(self, user_id: int) -> DBUser:
        db_user: DBUser = self.db.query(DBUser).filter(DBUser.id == user_id).first()

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким id не найден")

        return db_user

    def get_user_by_phone_number(self, phone_number: int) -> DBUser:
        db_user: DBUser = self.db.query(DBUser).filter(DBUser.phone_number == phone_number).first()

        return db_user

    def create_user(self, name: str, phone_number: int, password: str, token: str) -> DBUser:
        user_db_model = DBUser(
            name=name,
            phone_number=phone_number,
            password=password,
            access_token=token
        )

        if self.db is None:
            raise HTTPException(status_code=600, detail="Соединение с базой данных не установлено.")

        try:
            self.db.add(user_db_model)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            self.logger.error(f"IntegrityError: {str(e)}")  # Логируем ошибку
            raise HTTPException(status_code=409, detail="Пользователь с таким номером телефона уже зарегистрирован.")
        except Exception as e:
            self.logger.error(f"Exception: {str(e)}")  # Логируем ошибку
            self.db.rollback()
            raise HTTPException(status_code=500, detail="Ошибка сервера, попробуйте позже.")

        return user_db_model

    def update_user_info(self, access_token: str, name: str, phone_number: str) -> DBUser:
        db_user = self.get_user_by_access_token(access_token)

        db_user.name = name
        db_user.phone_number = phone_number

        self.db.commit()
        self.db.refresh(db_user)

        return db_user