import uuid
import bcrypt
from sqlite3 import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from DBmodels.DBUser import DBUser
from models.requests.SignInRequest import SignInRequest
from models.responses.SignInReposponse import SignInResponse
from models.User import User


class SSOService:
    @staticmethod
    def register_user(user: User, db: Session):
        """
        Регистрация нового пользователя.
        :param user: Данные нового пользователя
        :param db: Сессия базы данных
        :return: Сообщение об успешной регистрации
        """
        hashed_password = SSOService.hash_password(user.password)
        user_db_model = DBUser(
            name=user.name,
            phone_number=user.phone_number,
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

    @staticmethod
    def signin_user(credentials: SignInRequest, db: Session):
        """
        Авторизация пользователя.
        :param credentials: Входные данные (телефон, пароль)
        :param db: Сессия базы данных
        :return: Токен доступа
        """
        db_user = db.query(DBUser).filter(DBUser.phone_number == credentials.phone_number).first()

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким номером телефона не найден.")

        if not SSOService.verify_password(credentials.password, db_user.password):
            raise HTTPException(status_code=401, detail="Неверный пароль.")

        return SignInResponse(
            message="Успешная авторизация",
            access_token=db_user.access_token
        )

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Проверка пароля.
        :param plain_password: Обычный пароль
        :param hashed_password: Захешированный пароль
        :return: True/False
        """
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """
        Хеширование пароля.
        :param plain_password: Обычный пароль
        :return: Захешированный пароль (str)
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')