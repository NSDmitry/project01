from fastapi import APIRouter, Body, Depends, File, Request, UploadFile
from fastapi.params import Security

from app.core.models.response_model import ResponseModel
from app.core.params import QueryId
from app.core.rate_limit import client_ip, rate_limiter
from app.iam.deps import get_auth_service, get_current_user, get_user_service, session_header
from app.iam.models import User
from app.iam.schemas import (
    AuthUserResponse,
    ChangePasswordRequest,
    LoginAvailableRequest,
    LoginAvailableResponse,
    OwnUserResponse,
    SignInRequest,
    SignUpRequest,
    TelegramAuthRequest,
    UpdateUserRequest,
    UserSummary,
)
from app.iam.service import AuthService, UserService

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["Users"])

@auth_router.post(
    "/register",
    response_model=ResponseModel[AuthUserResponse],
    summary="SSO: Регистрация пользователя (номер телефона и пароль)",
    status_code=201,
    dependencies=[rate_limiter(times=5, seconds=60)],
    responses={
        201: {"description": "Успешный ответ с идентификатором сессии"},
        400: {"description": "Пароль не соответствует требованиям"},
        422: {"description": "Ошибка валидации номера телефона"},
        409: {"description": "Пользователь с таким номером телефона уже зарегистрирован"},
        429: {"description": "С этого адреса создано больше 3 аккаунтов за час"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def register(
    model: SignUpRequest,
    request: Request,
    sso_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[AuthUserResponse]:
    return await sso_service.register(model=model, client_ip=client_ip(request))

@auth_router.post(
    "/login",
    response_model = ResponseModel[AuthUserResponse],
    summary = "SSO: Авторизация пользователя (номер телефона и пароль)",
    dependencies=[rate_limiter(times=5, seconds=60)],
    responses = {
        200: {"description": "Успешный ответ с идентификатором сессии"},
        401: {"description": "Неверный номер телефона или пароль"},
        429: {"description": "Слишком много неудачных попыток входа - временная блокировка"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def login(
    model: SignInRequest,
    request: Request,
    sso_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[AuthUserResponse]:
    return await sso_service.login(model=model, client_ip=client_ip(request))

@auth_router.post(
    "/login-available",
    response_model=ResponseModel[LoginAvailableResponse],
    summary="SSO: Проверка доступности номера (авторизация или регистрация)",
    dependencies=[rate_limiter(times=10, seconds=60)],
    responses={
        200: {"description": "is_registered=true - номер занят (авторизация), false - свободен (регистрация)"},
        422: {"description": "Ошибка валидации номера телефона"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def login_available(
    model: LoginAvailableRequest,
    sso_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[LoginAvailableResponse]:
    return await sso_service.check_login_available(model=model)

@auth_router.post(
    "/telegram",
    response_model=ResponseModel[AuthUserResponse],
    summary="SSO: Вход и регистрация через Telegram Mini App (initData)",
    dependencies=[rate_limiter(times=10, seconds=60)],
    responses={
        200: {"description": "Успешный ответ с идентификатором сессии"},
        401: {"description": "Неверная подпись или устаревшие данные Telegram"},
        422: {"description": "Некорректное тело запроса"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def telegram(
    model: TelegramAuthRequest,
    sso_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[AuthUserResponse]:
    return await sso_service.login_with_telegram(model=model)

@auth_router.post(
    "/logout",
    response_model=ResponseModel[None],
    summary="SSO: Выход из системы (завершение текущей сессии по X-Session-Id)",
    responses={
        200: {"description": "Сессия завершена (если была активна)"},
        401: {"description": "Ошибка авторизации (отсутствует или невалиден X-Session-Id)"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def logout(
    sso_service: AuthService = Depends(get_auth_service),
    sid: str = Security(session_header),  # type: ignore[assignment]
) -> ResponseModel[None]:
    return await sso_service.logout(sid=sid)


@users_router.get(
    "/current",
    response_model=ResponseModel[OwnUserResponse],
    summary="Получение информации о текущем пользователе",
    description=
    """
    **Требуется авторизация** с заголовком:
    `X-Session-Id: <session_id>`
    """,
    responses={
        200: {"description": "Успешный ответ с данными пользователя"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def get_current_user_public_info(
    user: User = Depends(get_current_user)
) -> ResponseModel[OwnUserResponse]:
    return ResponseModel.ok(OwnUserResponse.model_validate(user))

@users_router.get(
    "/public",
    response_model=ResponseModel[UserSummary],
    summary="Получить публичную инфо о пользователе по ID",
    description=
    """
    **Требуется авторизация** с заголовком:
    `X-Session-Id: <session_id>`
    """,
    responses={
        200: {"description": "Успешный ответ с данными пользователя"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def get_user_by_id(
    user_id: QueryId,
    _: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> ResponseModel[UserSummary]:
    return await user_service.get_user_by_id(user_id)

@users_router.put(
    "",
    response_model=ResponseModel[OwnUserResponse],
    summary="Изменить данные о пользователе (имя и номер телефона)",
    responses={
        200: {"description": "Информация о пользователе успешно изменена"},
        404: {"description": "Пользователь не найден"},
        409: {"description": "Пользователь с таким номером телефона уже зарегистрирован"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def change_user_info(
    model: UpdateUserRequest = Body(...),
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> ResponseModel[OwnUserResponse]:
    return await user_service.update_user_info(user=user, model=model)


@users_router.put(
    "/avatar",
    response_model=ResponseModel[OwnUserResponse],
    summary="Загрузить аватар пользователя",
    description=
    """
    **Требуется авторизация** с заголовком:
    `X-Session-Id: <session_id>`

    Файл передаётся как `multipart/form-data`, поле `file`. Принимаются JPEG, PNG
    и WebP до 5 МБ; картинка уменьшается и сохраняется в WebP. Прежний аватар
    заменяется, ссылка на новый приходит в `avatar_url`.
    """,
    dependencies=[rate_limiter(times=10, seconds=60)],
    responses={
        200: {"description": "Аватар загружен, в ответе ссылка на него"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        413: {"description": "Файл больше 5 МБ или изображение слишком большое"},
        415: {"description": "Файл не изображение или формат не поддерживается"},
        429: {"description": "Слишком много загрузок"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> ResponseModel[OwnUserResponse]:
    return await user_service.update_avatar(user=user, file=file)


@users_router.put(
    "/password",
    response_model=ResponseModel[None],
    summary="Сменить пароль пользователя и завершить все активные сессии",
    dependencies=[rate_limiter(times=5, seconds=60)],
    responses={
        200: {"description": "Пароль успешно изменен, все сессии завершены"},
        400: {"description": "Новый пароль не соответствует policy"},
        401: {"description": "Неверный текущий пароль или отсутствует авторизация"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def change_password(
    model: ChangePasswordRequest = Body(...),
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[None]:
    return await auth_service.change_password(
        user=user,
        current_password=model.current_password,
        new_password=model.new_password,
    )


@users_router.delete(
    "/current",
    response_model=ResponseModel[None],
    summary="Удалить текущего пользователя (только свой аккаунт)",
    description=
    """
    **Требуется авторизация** с заголовком:
    `X-Session-Id: <session_id>`

    Флаги (по умолчанию `false`) управляют контентом пользователя:
    - `false` - клуб/тред/коммент отвязывается (owner/author -> null), но сохраняется;
    - `true` - удаляется вместе с вложенным содержимым.

    В теле запроса передаётся `password` - подтверждение пароля (не нужно для
    Telegram-аккаунтов без пароля).
    """,
    responses={
        200: {"description": "Аккаунт удалён, все сессии завершены"},
        400: {"description": "Не указан пароль для подтверждения"},
        401: {"description": "Ошибка авторизации или неверный пароль"},
        429: {"description": "Слишком много неверных паролей - номер временно заблокирован"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def delete_current_user(
    delete_clubs: bool = False,
    delete_threads: bool = False,
    delete_comments: bool = False,
    password: str | None = Body(default=None, embed=True),
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> ResponseModel[None]:
    return await auth_service.delete_current_user(
        user=user,
        password=password,
        delete_clubs=delete_clubs,
        delete_threads=delete_threads,
        delete_comments=delete_comments,
    )
