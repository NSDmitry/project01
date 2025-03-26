from fastapi import APIRouter, Depends

from app.schemas.sso_schema import SingUpRequestModel, SignInRequestModel, SignInResponseModel
from app.api.services.SSOService import SSOService

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post(
    "/signup",
    response_model=SignInResponseModel,
    summary="SSO: Регистрация пользователя (номер телефона и пароль)",
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
    summary = "SSO: Авторизация пользователя (номер телефона и пароль)",
    responses = {
        200: {"description": "Успешный ответ с данными пользователя"},
        201: {"description": "Неверный пароль"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def sign_in(model: SignInRequestModel, sso_service: SSOService = Depends()):
    return sso_service.sign_in(model=model)