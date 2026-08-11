import asyncio
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import UploadFile

from app.core import events, media
from app.core.errors.errors import Conflict, Unauthorized, BadRequest
from app.core.models.response_model import ResponseModel
from app.core.rate_limit import check_registrations_limit, count_registration
from app.iam import brute_force
from app.iam.models import User, UserSession
from app.iam.repository import UserRepository, UserSessionRepository
from app.iam.schemas import (
    AuthUserResponse,
    LoginAvailableRequest,
    LoginAvailableResponse,
    OwnUserResponse,
    SignInRequest,
    SignUpRequest,
    TelegramAuthRequest,
    UpdateUserRequest,
    UserSummary,
)
from app.iam.security.telegram import verify_init_data

LAST_USED_THRESHOLD = timedelta(minutes=5)
SESSION_MAX_IDLE = timedelta(days=30)
MAX_SESSIONS_PER_USER = 5


async def confirm_password(user: User, password: str) -> None:
    """Подтверждение пароля владельца аккаунта для чувствительных операций.

    Неудачные попытки идут в ту же эскалирующую блокировку, что и login, -
    иначе украденная сессия позволяет перебирать пароль в обход phone-lockout.
    """
    # Блокировка ключуется номером телефона, поэтому аккаунт без номера пустил бы
    # всех таких пользователей в один общий счётчик попыток.
    if user.phone_number is None or user.password is None:
        raise BadRequest(errors=["У аккаунта не установлен пароль"])

    await brute_force.check_not_locked(user.phone_number)

    if not await AuthService._verify_password(password, user.password):
        await brute_force.register_failure(user.phone_number)
        raise Unauthorized(errors=["Неверный текущий пароль"])

    await brute_force.reset(user.phone_number)


class UserService:
    user_repository: UserRepository

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_user_by_id(self, user_id: int) -> ResponseModel[UserSummary]:
        db_user: User = await self.user_repository.get_user_by_id(user_id)

        return ResponseModel.ok(UserSummary.model_validate(db_user))

    async def update_user_info(self, user: User, model: UpdateUserRequest) -> ResponseModel[OwnUserResponse]:
        await self.validate_phone_number(model.phone_number, exclude_user_id=user.id)
        updated_user: User = await self.user_repository.update_user_info(user.id, model.name, model.phone_number)

        return ResponseModel.ok(OwnUserResponse.model_validate(updated_user))

    async def update_avatar(self, user: User, file: UploadFile) -> ResponseModel[OwnUserResponse]:
        previous_key = user.avatar_key
        avatar_key = await media.store_image(media.AVATARS, file)
        updated_user: User = await self.user_repository.update_avatar(user, avatar_key)
        # ponytail: старый файл удаляем до коммита - если коммит упадёт, ссылка в
        # БД останется на удалённый файл. Станет важно - удалять по событию после
        # коммита; не удалять вовсе нельзя, хранилище растёт с каждой загрузкой.
        await media.delete_image(previous_key)

        return ResponseModel.ok(OwnUserResponse.model_validate(updated_user))

    async def validate_phone_number(self, phone_number: str, exclude_user_id: int | None = None) -> None:
        if not await self.__is_unique_phone_number(phone_number, exclude_user_id=exclude_user_id):
            raise Conflict(errors=["Пользователь с таким номером телефона уже зарегистрирован"])

    async def __is_unique_phone_number(self, phone_number: str, exclude_user_id: int | None = None) -> bool:
        user = await self.user_repository.get_user_by_phone_number(phone_number)

        return not (user and user.id != exclude_user_id)


class UserSessionService:
    user_session_repository: UserSessionRepository

    def __init__(self, user_session_repository: UserSessionRepository) -> None:
        self.user_session_repository = user_session_repository

    async def create_user_session(self, user_id: int) -> str:
        now = self._utcnow()

        sid = self._generate_sid()
        sid_hash = self._sid_hash(sid)

        await self.user_session_repository.create_user_session(
            user_id=user_id,
            sid_hash=sid_hash,
            last_used=now
        )
        # Не больше MAX_SESSIONS_PER_USER живых сессий - лишние (самые старые) удаляем.
        await self.user_session_repository.delete_sessions_over_limit(user_id, MAX_SESSIONS_PER_USER)

        return sid

    async def get_user_session(self, sid: str) -> UserSession:
        sid_hash = self._sid_hash(sid)
        session = await self.user_session_repository.get_user_session(sid_hash)

        if session is None:
            raise Unauthorized(errors=["Недействительная или истёкшая сессия"])

        now = self._utcnow()

        if session.last_used is None or session.last_used < now - SESSION_MAX_IDLE:
            raise Unauthorized(
                message="Сессия истекла из-за длительной неактивности",
                errors=["session_expired"],
            )

        if session.last_used < now - LAST_USED_THRESHOLD:
            await self.user_session_repository.update_last_used(session, now)

        return session

    async def logout_user_session(self, sid: str) -> None:
        sid_hash = self._sid_hash(sid)
        await self.user_session_repository.delete_user_session(sid_hash)

    async def logout_all_user_sessions(self, user_id: int) -> None:
        await self.user_session_repository.delete_all_user_sessions(user_id)

    async def cleanup_idle_sessions(self) -> int:
        cutoff = self._utcnow() - SESSION_MAX_IDLE
        return await self.user_session_repository.delete_idle_sessions(cutoff)

    @staticmethod
    def _generate_sid() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _sid_hash(sid: str) -> str:
        return hashlib.sha256(sid.encode("utf-8")).hexdigest()

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)


class AuthService:
    user_service: UserService
    user_session_service: UserSessionService
    user_repository: UserRepository
    telegram_bot_token: str

    def __init__(
            self,
            user_service: UserService,
            user_repository: UserRepository,
            user_session_service: UserSessionService,
            telegram_bot_token: str = ""
    ) -> None:
        self.user_service = user_service
        self.user_repository = user_repository
        self.user_session_service = user_session_service
        self.telegram_bot_token = telegram_bot_token

    async def register(self, model: SignUpRequest, client_ip: str) -> ResponseModel[AuthUserResponse]:
        """
        Регистрация нового пользователя.
        :param model: SignUpRequest
        :param client_ip: IP клиента - лимит на число созданных аккаунтов в час
        :return: Сообщение об успешной регистрации
        """

        await check_registrations_limit(client_ip)
        await self.user_service.validate_phone_number(model.phone_number)
        self.validate_password_policy(model.password)

        hashed_password = await self._hash_password(model.password)

        db_user = await self.user_repository.create_user(model.name, model.phone_number, hashed_password)
        await count_registration(client_ip)

        sid = await self.user_session_service.create_user_session(db_user.id)
        response = AuthUserResponse(session_id=sid)

        return ResponseModel.ok(response)

    async def login(self, model: SignInRequest, client_ip: str) -> ResponseModel[AuthUserResponse]:
        """
        Авторизация пользователя.
        :param model: SignInRequest
        :param client_ip: IP клиента - блокировка перебора паролей по случайным номерам
        :return: Токен доступа
        """
        # IP-лок проверяем первым: самая широкая отсечка, до похода в БД и до bcrypt.
        await brute_force.check_not_locked(client_ip, brute_force.IP)
        await brute_force.check_not_locked(model.phone_number)

        db_user = await self.user_repository.get_user_by_phone_number(model.phone_number)

        # Единый ответ для несуществующего номера и неверного пароля - не даём
        # отличить зарегистрированный номер от незарегистрированного (enumeration).
        # db_user.password is None - пользователь только из Telegram, пароля нет.
        if db_user is None or db_user.password is None:
            await brute_force.register_failure(model.phone_number)
            await brute_force.register_failure(client_ip, brute_force.IP)
            raise Unauthorized(errors=["Неверный номер телефона или пароль"])

        if not await self._verify_password(model.password, db_user.password):
            await brute_force.register_failure(model.phone_number)
            await brute_force.register_failure(client_ip, brute_force.IP)
            raise Unauthorized(errors=["Неверный номер телефона или пароль"])

        # Сбрасываем только телефонный счётчик. IP-счётчик намеренно не сбрасываем:
        # иначе атакующий с одним валидным аккаунтом обнуляет его каждые 19 неудач.
        await brute_force.reset(model.phone_number)
        sid = await self.user_session_service.create_user_session(db_user.id)
        response = AuthUserResponse(session_id=sid)

        return ResponseModel.ok(response)

    async def check_login_available(self, model: LoginAvailableRequest) -> ResponseModel[LoginAvailableResponse]:
        """
        Проверка доступности номера: занят - нужна авторизация, свободен - регистрация.
        :param model: LoginAvailableRequest
        :return: Флаг is_registered (True - номер зарегистрирован)
        """
        db_user = await self.user_repository.get_user_by_phone_number(model.phone_number)

        return ResponseModel.ok(LoginAvailableResponse(is_registered=db_user is not None))

    async def login_with_telegram(self, model: TelegramAuthRequest) -> ResponseModel[AuthUserResponse]:
        """
        Вход и регистрация через Telegram Mini App по подписанным данным инициализации.
        :param model: TelegramAuthRequest
        :return: Данные пользователя и идентификатор сессии
        """
        tg_user = verify_init_data(model.init_data, self.telegram_bot_token)

        telegram_id = int(tg_user["id"])
        name = tg_user.get("first_name") or tg_user.get("username") or f"tg_{telegram_id}"

        db_user = await self.user_repository.get_user_by_telegram_id(telegram_id)
        if db_user is None:
            db_user = await self.user_repository.create_telegram_user(telegram_id, name)

        sid = await self.user_session_service.create_user_session(db_user.id)
        response = AuthUserResponse(session_id=sid)

        return ResponseModel.ok(response)

    async def logout(self, sid: str | None) -> ResponseModel[None]:
        """
        Выход из системы (удаление сессии пользователя).
        :param sid: Идентификатор сессии
        :return: Сообщение об успешном выходе из системы
        """
        if not sid:
            raise Unauthorized(errors=["Отсутствует заголовок X-Session-Id"])

        await self.user_session_service.logout_user_session(sid)
        return ResponseModel.ok(message="Успешный выход из системы")

    async def change_password(self, user: User, current_password: str, new_password: str) -> ResponseModel[None]:
        # Telegram-пользователь: пароля нет, подтверждать и менять нечего.
        if user.password is None:
            raise BadRequest(errors=["У аккаунта не установлен пароль"])

        await confirm_password(user, current_password)

        self.validate_password_policy(new_password)

        if await self._verify_password(new_password, user.password):
            raise BadRequest(errors=["Новый пароль должен отличаться от текущего"])

        hashed_password = await self._hash_password(new_password)
        await self.user_repository.update_user_password(user.id, hashed_password)
        await self.user_session_service.logout_all_user_sessions(user.id)

        return ResponseModel.ok(
            None,
            message="Пароль обновлен. Все активные сессии завершены",
        )

    async def delete_current_user(
            self,
            user: User,
            password: str | None,
            delete_clubs: bool,
            delete_threads: bool,
            delete_comments: bool,
    ) -> ResponseModel[None]:
        # Необратимая операция - требуем пароль, а не только сессию.
        # У Telegram-пользователей пароля нет - подтверждать нечем, пропускаем.
        if user.password is not None:
            if not password:
                raise BadRequest(errors=["Для удаления аккаунта укажите пароль"])
            await confirm_password(user, password)

        # У bookclubs и threads нет FK на users - домены чистят свои данные
        # сами по событию user_deleted (bookclubs дальше публикует clubs_deleted
        # для тредов удалённых клубов). iam про эти домены не знает.
        await events.publish(
            events.USER_DELETED,
            {
                "user_id": user.id,
                "delete_clubs": delete_clubs,
                "delete_threads": delete_threads,
                "delete_comments": delete_comments,
            },
        )
        # Аватар - контент пользователя, вместе с аккаунтом уходит и он. Ключ читаем
        # до удаления строки: после него обращение к атрибуту пошло бы за строкой в БД.
        avatar_key = user.avatar_key
        await self.user_repository.delete_user(user_id=user.id)
        # user_sessions без FK на users - осиротевшие сессии удаляем вручную.
        await self.user_session_service.logout_all_user_sessions(user.id)
        await media.delete_image(avatar_key)

        return ResponseModel.ok(None, message="Аккаунт удалён")

    @staticmethod
    async def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Проверка пароля.
        :param plain_password: Обычный пароль
        :param hashed_password: Захешированный пароль
        :return: True/False
        """
        # bcrypt - CPU-bound и блокирует event loop, поэтому выносим в поток.
        return await asyncio.to_thread(
            bcrypt.checkpw, plain_password.encode('utf-8'), hashed_password.encode('utf-8')
        )

    @staticmethod
    async def _hash_password(plain_password: str) -> str:
        """
        Хеширование пароля.
        :param plain_password: Обычный пароль
        :return: Захешированный пароль (str)
        """

        def _hash() -> str:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
            return hashed.decode('utf-8')

        # bcrypt - CPU-bound и блокирует event loop, поэтому выносим в поток.
        return await asyncio.to_thread(_hash)

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
