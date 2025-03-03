from fastapi import APIRouter, Depends

from services.SSO.Models import SingUpRequestModel, SignInRequestModel, SignInResponseModel
from services.SSO.SSOService import SSOService

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post(
    "/signup",
    response_model=SignInResponseModel,
    summary="Регистрация пользователя по номеру телефона и паролю",
    responses={
        200: {"description": "Успешный ответ с данными пользователя"},
        400: {"description": "Ошибка валидации номера телефона или пароля"},
        409: {"description": "Пользователь с таким номером телефона уже зарегистрирован"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def sign_up(model: SingUpRequestModel, sso_service: SSOService = Depends()):
    return sso_service.sign_up(model=model)

@router.post(
    "/signin",
    response_model = SignInResponseModel,
    summary = "Авторизация пользователя по номеру телефона и паролю",
    responses = {
        200: {"description": "Успешный ответ с данными пользователя"},
        201: {"description": "Неверный пароль"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def sign_in(model: SignInRequestModel, sso_service: SSOService = Depends()):
    return sso_service.sign_in(model=model)