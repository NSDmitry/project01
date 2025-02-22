import uuid
import bcrypt

from sqlalchemy.orm import Session
from fastapi import HTTPException

from repositories.UserRepository import UserRepository
from services.SSO.Models import SingUpRequestModel, SignInRequestModel, SignInResponseModel
from services.User.Models import PublicUserResponseModel
from services.User.UserService import UserSerivce


class SSOService:
    @classmethod
    def sign_up(cls, model: SingUpRequestModel, db: Session) -> SignInResponseModel:
        """
        Регистрация нового пользователя.
        :param model: SingUpRequestModel
        :param db: Session
        :return: Сообщение об успешной регистрации
        """

        UserSerivce.validate_phone_number(model.phone_number, db)
        UserSerivce.is_unique_phone_number(model.phone_number, db)

        hashed_password = cls.__hash_password(model.password)

        db_user = UserRepository.create_user(model.name, model.phone_number, hashed_password, str(uuid.uuid4()), db)

        return SignInResponseModel(
            message="Пользователь успешно зарегистрирован",
            access_token=db_user.access_token,
            model=PublicUserResponseModel.from_db_model(db_model=db_user)
        )

    @classmethod
    def sign_in(cls, model: SignInRequestModel, db: Session) -> SignInResponseModel:
        """
        Авторизация пользователя.
        :param model: SignInRequestModel
        :param db: Session
        :return: Токен доступа
        """
        db_user = UserRepository.get_user_by_phone_number(model.phone_number, db)

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