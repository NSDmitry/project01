from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from DBmodels import DBUser
from services.OAuth2PasswordBearer.OAuth2PasswordBearer import get_current_user


class UserRepository:
    @classmethod
    def get_user_by_access_token(cls, access_token: str, db: Session) -> DBUser:
        return get_current_user(access_token, db)

    @classmethod
    def get_user_by_id(cls, user_id: int, db: Session) -> DBUser:
        db_user: DBUser = db.query(DBUser).filter(DBUser.id == user_id).first()

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким id не найден")

        return db_user

    @classmethod
    def get_user_by_phone_number(cls, phone_number: int, db: Session) -> DBUser:
        db_user: DBUser = db.query(DBUser).filter(DBUser.phone_number == phone_number).first

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким id не найден")

        return db_user

    @classmethod
    def create_user(cls, name: str, phone_number: int, password: str, token: str, db: Session) -> DBUser:
        user_db_model = DBUser(
            name=name,
            phone_number=phone_number,
            password=password,
            access_token=token
        )

        try:
            db.add(user_db_model)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Пользователь с таким номером телефона уже зарегистрирован.")
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Ошибка сервера, попробуйте позже.")

        return user_db_model

    @classmethod
    def update_user_info(cls, access_token: str, name: str, phone_number: str, db: Session) -> DBUser:
        db_user = UserRepository.get_user_by_access_token(access_token, db)

        db_user.name = name
        db_user.phone_number = phone_number

        db.commit()
        db.refresh(db_user)

        return db_user