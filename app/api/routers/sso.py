from fastapi import APIRouter, Depends

from app.core.models.response_model import ResponseModel
from app.schemas.public_user_schema import PrivateUserResponseModel
from app.schemas.sso_schema import SingUpRequestModel, SignInRequestModel, TelegramSignInRequestModel
from app.api.services.sso_service import SSOService

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post(
    "/signup",
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
def sign_up(model: SingUpRequestModel, sso_service: SSOService = Depends()):
    return sso_service.sign_up(model=model)

@router.post(
    "/signin",
    response_model = ResponseModel[PrivateUserResponseModel],
    summary = "SSO: Авторизация пользователя (номер телефона и пароль)",
    responses = {
        200: {"description": "Успешный ответ с данными пользователя"},
        401: {"description": "Неверный пароль"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def sign_in(model: SignInRequestModel, sso_service: SSOService = Depends()):
    return sso_service.sign_in(model=model)

@router.post(
    "/telegram/signin",
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
    sso_service: SSOService = Depends()
):
    return sso_service.telegram_sing_in(model=model)