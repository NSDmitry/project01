from fastapi import APIRouter, Body, Depends
from fastapi.params import Security

from app.core.models.response_model import ResponseModel
from app.iam.deps import get_auth_service, get_current_user, get_user_service, session_header
from app.iam.models import User
from app.iam.schemas import (
    AuthUserResponse,
    ChangePasswordRequest,
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
    responses={
        201: {"description": "Успешный ответ с идентификатором сессии"},
        422: {"description": "Ошибка валидации номера телефона или пароля"},
        409: {"description": "Пользователь с таким номером телефона уже зарегистрирован"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def register(
    model: SignUpRequest,
    sso_service: AuthService = Depends(get_auth_service)
):
    return await sso_service.register(model=model)

@auth_router.post(
    "/login",
    response_model = ResponseModel[AuthUserResponse],
    summary = "SSO: Авторизация пользователя (номер телефона и пароль)",
    responses = {
        200: {"description": "Успешный ответ с идентификатором сессии"},
        401: {"description": "Неверный пароль"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def login(
    model: SignInRequest,
    sso_service: AuthService = Depends(get_auth_service)
):
    return await sso_service.login(model=model)

@auth_router.post(
    "/telegram",
    response_model=ResponseModel[AuthUserResponse],
    summary="SSO: Вход и регистрация через Telegram Mini App (initData)",
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
):
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
    sid: str = Security(session_header)
):
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
):
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
    user_id: int,
    _: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_user_by_id(user_id)

@users_router.put(
    "",
    response_model=ResponseModel[OwnUserResponse],
    summary="Изменить данные о пользователе (имя и номер телефона)",
    responses={
        200: {"description": "Информация о пользователе успешно изменена"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def change_user_info(
    model: UpdateUserRequest = Body(...),
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.update_user_info(user=user, model=model)


@users_router.put(
    "/password",
    response_model=ResponseModel[None],
    summary="Сменить пароль пользователя и завершить все активные сессии",
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
):
    return await auth_service.change_password(
        user=user,
        current_password=model.current_password,
        new_password=model.new_password,
    )
