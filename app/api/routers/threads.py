from fastapi import APIRouter, Depends, Query

from app.api.services.thread_service import ThreadService
from app.core.deps.deps import get_thread_service
from app.core.deps.get_current_user import get_current_user
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.db.models import DBUser
from app.schemas.threads_schema import ThreadResponseModel, ThreadCreateRequestModel, \
    ThreadUpdateRequestModel

router = APIRouter(prefix="/api/threads", tags=["threads"])

@router.get(
    "/{club_id}",
    response_model=ResponseModel[Page[ThreadResponseModel]],
    summary="Получение тредов книжного клуба (постранично, последние сверху)",
    description="",
    responses={
        200: {"description": "Страница тредов клуба"},
        404: {"description": "Книжный клуб с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_threads(
    club_id: int,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ThreadService = Depends(get_thread_service)
):
    return await service.get_threads(book_club_id=club_id, limit=limit, offset=offset)

@router.post(
    "",
    response_model=ResponseModel[ThreadResponseModel],
    summary="Создание треда",
    description=(
        "Создание треда в книжном клубе.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными треда"},
        400: {"description": "Ошибка валидации данных треда"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб с таким id не найден"},
        403: {"description": "Создавать треды могут только участники клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def create_thread(
    model: ThreadCreateRequestModel,
    user: DBUser = Depends(get_current_user),
    service: ThreadService = Depends(get_thread_service)
):
    return await service.create_thread(user=user, model=model)

@router.delete(
    "/{thread_id}",
    response_model=ResponseModel,
    summary="Удаление треда",
    status_code=200,
    responses={
        200: {"description": "Тред успешно удалён"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Тред с таким id не найден"},
        403: {"description": "Удалять треды может только автор треда"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def delete_thread(
    thread_id: int,
    user: DBUser = Depends(get_current_user),
    service: ThreadService = Depends(get_thread_service)
):
    return await service.delete_thread(user=user, thread_id=thread_id)

@router.put(
    "/{thread_id}",
    response_model=ResponseModel[ThreadResponseModel],
    status_code=200,
    responses={
        200: {"description": "Тред успешно обновлён"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Тред с таким id не найден"},
        403: {"description": "Изменять тред может только автор треда, или владелец клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def update_thread(
    thread_id: int,
    model: ThreadUpdateRequestModel,
    user: DBUser = Depends(get_current_user),
    service: ThreadService = Depends(get_thread_service)
):
    return await service.update_thread(user=user, thread_id=thread_id, model=model)
