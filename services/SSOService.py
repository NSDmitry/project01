import uuid
import bcrypt
from sqlite3 import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from DBmodels.DBUser import DBUser

class SSOService:
    @classmethod
    def register_user(cls, name: str, phone_number: str, password: str, db: Session):
        """
        Регистрация нового пользователя.
        :param name: имя пользователя
        :param phone_number: номер телефона
        :param password: пароль пользователя
        :param db: Сессия базы данных
        :return: Сообщение об успешной регистрации
        """
        hashed_password = cls.__hash_password(password)
        user_db_model = DBUser(
            name=name,
            phone_number=phone_number,
            password=hashed_password,
            access_token=str(uuid.uuid4())
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

        return {"message": "Пользователь успешно зарегистрирован"}

    @classmethod
    def signin_user(cls, phone_number: str, password: str, db: Session):
        """
        Авторизация пользователя.
        :param phone_number: номер телефона
        :param password: пароль пользователя
        :param db: Сессия базы данных
        :return: Токен доступа
        """
        db_user = db.query(DBUser).filter(DBUser.phone_number == phone_number).first()

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким номером телефона не найден.")

        if not cls.__verify_password(password, db_user.password):
            raise HTTPException(status_code=401, detail="Неверный пароль.")

        return {
            "message": "Успешная авторизация",
            "access_token": db_user.access_token
        }

    @classmethod
    def __verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """
        Проверка пароля.
        :param plain_password: Обычный пароль
        :param hashed_password: Захешированный пароль
        :return: True/False
        """
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    @classmethod
    def __hash_password(cls, plain_password: str) -> str:
        """
        Хеширование пароля.
        :param plain_password: Обычный пароль
        :return: Захешированный пароль (str)
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')