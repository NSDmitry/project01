from typing import List

from fastapi import APIRouter, Depends

from app.api.services.discussion_service import DiscussionService
from app.core.OAuth2PasswordBearer import oauth2_scheme
from app.core.models.response_model import ResponseModel
from app.schemas.discussions_schema import DisscussionResponseModel, DiscussionCreateRequestModel

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
def get_disscussions(club_id: int, service: DiscussionService = Depends()):
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
    responses={
        200: {"description": "Успешный ответ с данными обсуждения"},
        400: {"description": "Ошибка валидации данных обсуждения"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб с таким id не найден"},
        409: {"description": "Создавать обсуждения могут только участники клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
def create_discussion(
    model: DiscussionCreateRequestModel,
    access_token: str = Depends(oauth2_scheme),
    service: DiscussionService = Depends()
):
    return service.create_discussion(access_token=access_token, model=model)