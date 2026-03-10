import uuid
import re
import bcrypt

from app.api.services.user_session_service import UserSessionService
from app.core.errors.errors import NotFound, Unauthorized, BadRequest
from app.core.models.response_model import ResponseModel
from app.db.repositories.user_repository import UserRepository
from app.schemas.sso_schema import SingUpRequestModel, SignInRequestModel, TelegramSignInRequestModel
from app.schemas.public_user_schema import PrivateUserResponseModel
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
        self.validate_password_policy(model.password)

        hashed_password = self._hash_password(model.password)

        db_user = self.user_repository.create_user(model.name, model.phone_number, hashed_password)
        sid = self.user_session_service.create_user_session(db_user.id)
        response = self._make_auth_response(db_user, sid)

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

        if not self._verify_password(model.password, db_user.password):
            raise Unauthorized(errors=["Неверный пароль"])

        sid = self.user_session_service.create_user_session(db_user.id)

        if not sid:
            raise BadRequest(errors=["Не удалось создать сессию пользователя"])

        response = self._make_auth_response(db_user, sid)

        return ResponseModel.success_response(response)

    def logout(self, sid: str | None) -> ResponseModel[None]:
        """
        Выход из системы (удаление сессии пользователя).
        :param sid: Идентификатор сессии
        :return: Сообщение об успешном выходе из системы
        """
        if not sid:
            raise Unauthorized(errors=["Missing session"])

        self.user_session_service.logout_user_session(sid)
        return ResponseModel.success_response(None, message="Успешный выход из системы")

    def telegram_login(self, model: TelegramSignInRequestModel) -> ResponseModel[PrivateUserResponseModel]:
        db_user = self.user_repository.get_user_by_telegram_id(model.telegram_id)

        if db_user:
            sid = self.user_session_service.create_user_session(db_user.id)
            response = self._make_auth_response(db_user, sid)
            return ResponseModel.success_response(response)
        else:
            hashed_password = self._hash_password(str(uuid.uuid4()))

            new_user = self.user_repository.create_user_by_telegram(
                model.telegram_id,
                hashed_password,
                model.name
            )

            sid = self.user_session_service.create_user_session(new_user.id)
            response = self._make_auth_response(new_user, sid)

            return ResponseModel.success_response(response)

    def change_password(self, user, current_password: str, new_password: str) -> ResponseModel[None]:
        if not self._verify_password(current_password, user.password):
            raise Unauthorized(errors=["Неверный текущий пароль"])

        self.validate_password_policy(new_password)

        if self._verify_password(new_password, user.password):
            raise BadRequest(errors=["Новый пароль должен отличаться от текущего"])

        hashed_password = self._hash_password(new_password)
        self.user_repository.update_user_password(user.id, hashed_password)
        self.user_session_service.logout_all_user_sessions(user.id)

        return ResponseModel.success_response(
            None,
            message="Пароль обновлен. Все активные сессии завершены",
        )

    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Проверка пароля.
        :param plain_password: Обычный пароль
        :param hashed_password: Захешированный пароль
        :return: True/False
        """
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    @staticmethod
    def _hash_password(plain_password: str) -> str:
        """
        Хеширование пароля.
        :param plain_password: Обычный пароль
        :return: Захешированный пароль (str)
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def validate_password_policy(password: str) -> None:
        if len(password) < 8:
            raise BadRequest(errors=["Пароль должен быть не короче 8 символов"])
        if len(password) > 128:
            raise BadRequest(errors=["Пароль должен быть не длиннее 128 символов"])
        if password.strip() != password or not password.strip():
            raise BadRequest(errors=["Пароль не должен быть пустым или состоять только из пробелов"])
        if not re.search(r"[A-Z]", password):
            raise BadRequest(errors=["Пароль должен содержать хотя бы одну заглавную букву"])
        if not re.search(r"[a-z]", password):
            raise BadRequest(errors=["Пароль должен содержать хотя бы одну строчную букву"])
        if not re.search(r"\d", password):
            raise BadRequest(errors=["Пароль должен содержать хотя бы одну цифру"])

    @staticmethod
    def _make_auth_response(db_user, sid: str) -> PrivateUserResponseModel:
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
