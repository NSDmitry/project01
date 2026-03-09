from fastapi import APIRouter, Depends
from fastapi.params import Security
from pydantic import Secret

from app.core.deps.deps import get_auth_service
from app.core.deps.get_current_user import session_header
from app.core.models.response_model import ResponseModel
from app.schemas.public_user_schema import PrivateUserResponseModel
from app.schemas.sso_schema import SingUpRequestModel, SignInRequestModel, TelegramSignInRequestModel
from app.api.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post(
    "/register",
    response_model=ResponseModel[PrivateUserResponseModel],
    summary="SSO: Регистрация пользователя (номер телефона и пароль)",
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными пользователя"},
        422: {"description": "Ошибка валидации номера телефона или пароля"},
        409: {"description": "Пользователь с таким номером телефона уже зарегистрирован"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def register(
    model: SingUpRequestModel,
    sso_service: AuthService = Depends(get_auth_service)
):
    return sso_service.register(model=model)

@router.post(
    "/login",
    response_model = ResponseModel[PrivateUserResponseModel],
    summary = "SSO: Авторизация пользователя (номер телефона и пароль)",
    responses = {
        200: {"description": "Успешный ответ с данными пользователя"},
        401: {"description": "Неверный пароль"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def login(
    model: SignInRequestModel,
    sso_service: AuthService = Depends(get_auth_service)
):
    return sso_service.login(model=model)

@router.post(
    "/logout",
    response_model=ResponseModel[None],
    summary="SSO: Выход из системы (завершение текущей сессии по X-Session-Id)",
    responses={
        200: {"description": "Сессия завершена (если была активна)"},
        401: {"description": "Ошибка авторизации (отсутствует или невалиден X-Session-Id)"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def logout(
    sso_service: AuthService = Depends(get_auth_service),
    sid: str = Security(session_header)
):
    return sso_service.logout(sid=sid)

@router.post(
    "/telegram/login",
    response_model=ResponseModel[PrivateUserResponseModel],
    summary="SSO: Авторизация через Telegram. Если пользователь не зарегистрирован, то он будет зарегистрирован автоматически",
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными пользователя"},
        422: {"description": "Ошибка валидации Telegram ID"},
        409: {"description": "Пользователь с таким номером телефона уже зарегистрирован"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def telegram_sign_in(
    model: TelegramSignInRequestModel,
    sso_service: AuthService = Depends(get_auth_service)
):
    return sso_service.telegram_login(model=model)
