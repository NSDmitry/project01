from fastapi import APIRouter, Depends, Body

from app.core.deps.deps import get_user_service, get_auth_service
from app.core.deps.get_current_user import get_current_user
from app.api.services.auth_service import AuthService
from app.api.services.user_service import UserService, PublicUserResponseModel, UpdateUserRequestModel
from app.core.models.response_model import ResponseModel
from app.db.models import DBUser
from app.schemas.public_user_schema import ChangePasswordRequestModel

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get(
    "/current",
    response_model=ResponseModel[PublicUserResponseModel],
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
def get_current_user_public_info(
    user: DBUser = Depends(get_current_user)
):
    return ResponseModel.success_response(PublicUserResponseModel(**user.to_dict()))

@router.get(
    "/public",
    response_model=ResponseModel[PublicUserResponseModel],
    summary="Получить публичную инфо о пользователе по ID",
    description=
    """
    **Требуется авторизация** с заголовком:  
    `Authorization: Bearer <your_token>`
    """,
    responses={
        200: {"description": "Успешный ответ с данными пользователя"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def get_user_by_id(
    user_id: int,
    _: DBUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    return user_service.get_user_by_id(user_id)

@router.put(
    "",
    response_model=ResponseModel[PublicUserResponseModel],
    summary="Изменить публичные данные о пользователе (имя и номер телефона)",
    responses={
        200: {"description": "Информация о пользователе успешно изменена"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def change_user_info(
    model: UpdateUserRequestModel = Body(...),
    user: DBUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    return user_service.update_user_info(user=user, model=model)


@router.put(
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
def change_password(
    model: ChangePasswordRequestModel = Body(...),
    user: DBUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    return auth_service.change_password(
        user=user,
        current_password=model.current_password,
        new_password=model.new_password,
    )
