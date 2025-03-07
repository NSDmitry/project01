import uuid
import bcrypt

from fastapi import HTTPException

from repositories.UserRepository import UserRepository
from services.SSO.Models import SingUpRequestModel, SignInRequestModel, SignInResponseModel
from services.User.Models import PublicUserResponseModel
from services.User.UserService import UserService


class SSOService:
    user_service: UserService
    user_repository: UserRepository

    def __init__(self) -> None:
        self.user_service = UserService()
        self.user_repository = UserRepository()

    def sign_up(self, model: SingUpRequestModel) -> SignInResponseModel:
        """
        Регистрация нового пользователя.
        :param model: SingUpRequestModel
        :return: Сообщение об успешной регистрации
        """

        self.user_service.validate_phone_number(model.phone_number)

        hashed_password = self.__hash_password(model.password)

        db_user = self.user_repository.create_user(model.name, model.phone_number, hashed_password, str(uuid.uuid4()))

        return SignInResponseModel(
            message="Пользователь успешно зарегистрирован",
            access_token=db_user.access_token,
            model=PublicUserResponseModel.from_db_model(db_model=db_user)
        )

    def sign_in(self, model: SignInRequestModel) -> SignInResponseModel:
        """
        Авторизация пользователя.
        :param model: SignInRequestModel
        :return: Токен доступа
        """
        db_user = self.user_repository.get_user_by_phone_number(model.phone_number)

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким номером телефона не найден.")

        if not self.__verify_password(model.password, db_user.password):
            raise HTTPException(status_code=401, detail="Неверный пароль.")

        return SignInResponseModel(
            message="Успешная авторизация",
            access_token=db_user.access_token,
            model=PublicUserResponseModel.from_db_model(db_user)
        )

    def __verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверка пароля.
        :param plain_password: Обычный пароль
        :param hashed_password: Захешированный пароль
        :return: True/False
        """
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    def __hash_password(self, plain_password: str) -> str:
        """
        Хеширование пароля.
        :param plain_password: Обычный пароль
        :return: Захешированный пароль (str)
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')