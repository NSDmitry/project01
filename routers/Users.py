from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.OAuth2PasswordBearer.OAuth2PasswordBearer import oauth2_scheme
from services.User.UserService import UserService, PublicUserResponseModel, UpdateUserRequestModel

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get(
    "/current",
    response_model=PublicUserResponseModel,
    summary="Получение публичной информации о текущем пользвателе",
    description=
    """
    **Требуется авторизация** с заголовком:  
    `Authorization: Bearer <your_token>`
    """,
    responses={
        200: {"description": "Успешный ответ с данными пользователя"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def get_current_user(access_token: str = Depends(oauth2_scheme), user_service: UserService = Depends()):
    return user_service.get_current_user(access_token)

@router.get(
    "/public",
    response_model=PublicUserResponseModel,
    summary="Получить публичную инфо о пользователе по ID",
    responses={
        200: {"description": "Успешный ответ с данными пользователя"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def get_user_by_id(user_id: int, user_service: UserService = Depends()):
    return user_service.get_user_by_id(user_id)

@router.put(
    "",
    response_model=PublicUserResponseModel,
    summary="Изменить публичные данные о пользователе (имя и номер телефона)",
    responses={
        200: {"description": "Информация о пользователе успешно изменена"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def change_user_info(
        model: UpdateUserRequestModel,
        access_token: str = Depends(oauth2_scheme),
        user_service = Depends()):
    return user_service.update_user_info(access_token=access_token, model=model)
