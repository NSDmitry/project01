import uuid
import bcrypt
from sqlite3 import IntegrityError

from sqlalchemy.orm import Session
from fastapi import HTTPException

from DBmodels.DBUser import DBUser
from services.SSO.Models import SingUpRequestModel, SignInRequestModel, SignInResponseModel
from services.User.Models import PublicUserResponseModel


class SSOService:
    @classmethod
    def sign_up(cls, model: SingUpRequestModel, db: Session) -> SignInResponseModel:
        """
        Регистрация нового пользователя.
        :param model: SingUpRequestModel
        :param db: Session
        :return: Сообщение об успешной регистрации
        """
        hashed_password = cls.__hash_password(model.password)
        user_db_model = DBUser(
            name=model.name,
            phone_number=model.phone_number,
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

        return SignInResponseModel(
            message="Пользователь успешно зарегистрирован",
            access_token=user_db_model.access_token,
            model=PublicUserResponseModel.from_db_model(db_model=user_db_model)
        )

    @classmethod
    def sign_in(cls, model: SignInRequestModel, db: Session) -> SignInResponseModel:
        """
        Авторизация пользователя.
        :param model: SignInRequestModel
        :param db: Session
        :return: Токен доступа
        """
        db_user = db.query(DBUser).filter(DBUser.phone_number == model.phone_number).first()

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким номером телефона не найден.")

        if not cls.__verify_password(model.password, db_user.password):
            raise HTTPException(status_code=401, detail="Неверный пароль.")

        return SignInResponseModel(
            message="Успешная авторизация",
            access_token=db_user.access_token,
            model=PublicUserResponseModel.from_db_model(db_user)
        )

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