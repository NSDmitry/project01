import uuid
import bcrypt

from app.api.services.user_session_service import UserSessionService
from app.core.errors.APIExeption import APIException
from app.core.errors.errors import NotFound, Unauthorized, BadRequest
from app.core.models.response_model import ResponseModel
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.user_session_repository import UserSessionRepository
from app.schemas.sso_schema import SingUpRequestModel, SignInRequestModel, TelegramSignInRequestModel
from app.schemas.public_user_schema import PublicUserResponseModel, PrivateUserResponseModel
from app.api.services.user_service import UserService


class AuthService:
    user_service: UserService
    user_session_service: UserSessionService
    user_repository: UserRepository

    def __init__(
        self,
        user_service: UserService,
        user_repository: UserRepository,
        user_session_service: UserSessionService
    ) -> None:
        self.user_service = user_service
        self.user_repository = user_repository
        self.user_session_service = user_session_service

    def register(self, model: SingUpRequestModel) -> ResponseModel[PrivateUserResponseModel]:
        """
        Регистрация нового пользователя.
        :param model: SingUpRequestModel
        :return: Сообщение об успешной регистрации
        """

        self.user_service.validate_phone_number(model.phone_number)

        hashed_password = self.__hash_password(model.password)

        db_user = self.user_repository.create_user(model.name, model.phone_number, hashed_password)
        sid = self.user_session_service.create_user_session(db_user.id)
        response = self.__make_auth_response(db_user, sid)

        return ResponseModel.success_response(response)


    def login(self, model: SignInRequestModel) -> ResponseModel[PrivateUserResponseModel] :
        """
        Авторизация пользователя.
        :param model: SignInRequestModel
        :return: Токен доступа
        """
        db_user = self.user_repository.get_user_by_phone_number(model.phone_number)

        if db_user is None:
            raise NotFound(errors=["Пользователь не найден"])

        sid = self.user_session_service.create_user_session(db_user.id)

        if not sid:
            raise BadRequest(errors=["Не удалось создать сессию пользователя"])

        if not self.__verify_password(model.password, db_user.password):
            raise Unauthorized(errors=["Неверный пароль"])

        response = self.__make_auth_response(db_user, sid)

        return ResponseModel.success_response(response)

    def telegram_login(self, model: TelegramSignInRequestModel) -> ResponseModel[PrivateUserResponseModel]:
        db_user = self.user_repository.get_user_by_telegram_id(model.telegram_id)

        if db_user:
            sid = self.user_session_service.create_user_session(db_user.id)
            response = self.__make_auth_response(db_user, sid)
            return ResponseModel.success_response(response)
        else:
            hashed_password = self.__hash_password(str(uuid.uuid4()))

            new_user = self.user_repository.create_user_by_telegram(
                model.telegram_id,
                hashed_password,
                model.name,
                str(uuid.uuid4())
            )

            sid = self.user_session_service.create_user_session(db_user.id)
            response = self.__make_auth_response(new_user, sid)

            return ResponseModel.success_response(response)

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

    def __make_auth_response(self, db_user, sid: str) -> PrivateUserResponseModel:
        payload = {
            "id": db_user.id,
            "name": db_user.name,
            "phone_number": db_user.phone_number,
            "created_at": db_user.created_at,
            "session_id": sid,
            "is_telegram_user": db_user.is_telegram_user,
            "telegram_id": db_user.telegram_id
        }

        return PrivateUserResponseModel(**payload)