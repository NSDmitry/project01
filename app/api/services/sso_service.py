import uuid
import bcrypt

from app.core.errors.APIExeption import APIException
from app.core.errors.errors import NotFound, Unauthorized
from app.core.models.response_model import ResponseModel
from app.db.repositories.user_repository import UserRepository
from app.schemas.sso_schema import SingUpRequestModel, SignInRequestModel, TelegramSignInRequestModel
from app.schemas.public_user_schema import PublicUserResponseModel, PrivateUserResponseModel
from app.api.services.user_service import UserService


class SSOService:
    user_service: UserService
    user_repository: UserRepository

    def __init__(self) -> None:
        self.user_service = UserService()
        self.user_repository = UserRepository()

    def sign_up(self, model: SingUpRequestModel) -> ResponseModel[PrivateUserResponseModel]:
        """
        Регистрация нового пользователя.
        :param model: SingUpRequestModel
        :return: Сообщение об успешной регистрации
        """

        self.user_service.validate_phone_number(model.phone_number)

        hashed_password = self.__hash_password(model.password)

        db_user = self.user_repository.create_user(model.name, model.phone_number, hashed_password, str(uuid.uuid4()))

        return ResponseModel.success_response(PrivateUserResponseModel(**db_user.to_dict()))


    def sign_in(self, model: SignInRequestModel) -> ResponseModel[PrivateUserResponseModel] :
        """
        Авторизация пользователя.
        :param model: SignInRequestModel
        :return: Токен доступа
        """
        db_user = self.user_repository.get_user_by_phone_number(model.phone_number)

        if db_user is None:
            raise NotFound(errors=["Пользователь не найден"])

        if not self.__verify_password(model.password, db_user.password):
            raise Unauthorized(errors=["Неверный пароль"])

        return ResponseModel.success_response(PrivateUserResponseModel(**db_user.to_dict()))

    def telegram_sing_in(self, model: TelegramSignInRequestModel) -> ResponseModel[PrivateUserResponseModel]:
        db_user = self.user_repository.get_user_by_telegram_id(model.telegram_id)

        if db_user:
            return ResponseModel.success_response(PrivateUserResponseModel(**db_user.to_dict()))
        else:
            hashed_password = self.__hash_password(str(uuid.uuid4()))

            new_user = self.user_repository.create_user_by_telegram(
                model.telegram_id,
                hashed_password,
                model.name,
                str(uuid.uuid4())
            )
            
            return ResponseModel.success_response(PrivateUserResponseModel(**new_user.to_dict()))

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