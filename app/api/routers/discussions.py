from typing import List

from fastapi import APIRouter, Depends

from app.api.services.discussion_service import DiscussionService
from app.core.deps.deps import get_discussion_service
from app.core.deps.get_current_user import get_current_user
from app.core.models.response_model import ResponseModel
from app.db.models import DBUser
from app.schemas.discussions_schema import DisscussionResponseModel, DiscussionCreateRequestModel, \
    DiscussionUpdateRequestModel

router = APIRouter(prefix="/api/disscussions", tags=["discussions"])

@router.get(
    "/{club_id}",
    response_model=ResponseModel[List[DisscussionResponseModel]],
    summary="Получение всех обсуждений книжного клуба",
    description="",
    responses={
        200: {"description": "Успешный ответ с данными обсуждений"},
        404: {"description": "Книжный клуб с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
def get_disscussions(
    club_id: int,
    service: DiscussionService = Depends(get_discussion_service)
):
    return service.get_disscussions(book_club_id=club_id)

@router.post(
    "",
    response_model=ResponseModel[DisscussionResponseModel],
    summary="Создание обсуждения",
    description=(
        "Создание обсуждения в книжном клубе.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`Authorization: Bearer <your_token>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными обсуждения"},
        400: {"description": "Ошибка валидации данных обсуждения"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб с таким id не найден"},
        409: {"description": "Создавать обсуждения могут только участники клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def create_discussion(
    model: DiscussionCreateRequestModel,
    user: DBUser = Depends(get_current_user),
    service: DiscussionService = Depends(get_discussion_service)
):
    return service.create_discussion(user=user, model=model)

@router.delete(
    "/{discussion_id}",
    response_model=ResponseModel,
    summary="Удаление обсуждения",
    status_code=200,
    responses={
        200: {"description": "Обсуждение успешно удалено"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Обсуждение с таким id не найдено"},
        409: {"description": "Удалять обсуждения может только автор обсуждения"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def delete_discussion(
    discussion_id: int,
    user: DBUser = Depends(get_current_user),
    service: DiscussionService = Depends(get_discussion_service)
):
    return service.delete_discussion(user=user, discussion_id=discussion_id)

@router.put(
    "/{discussion_id}",
    response_model=ResponseModel[DisscussionResponseModel],
    status_code=200,
    responses={
        200: {"description": "Обсуждение успешно обновлено"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Обсуждение с таким id не найдено"},
        409: {"description": "Удалять обсуждения может только автор обсуждения, или владелец клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def update_discussion(
    discussion_id: int,
    model: DiscussionUpdateRequestModel,
    user: str = Depends(get_current_user),
    service: DiscussionService = Depends(get_discussion_service)
):
    return service.update_discussion(user=user, discussion_id=discussion_id, model=model)