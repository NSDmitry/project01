from fastapi import APIRouter, Depends, Query

from app.api.services.comment_service import CommentService
from app.core.deps.deps import get_comment_service
from app.core.deps.get_current_user import get_current_user
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.db.models import DBUser
from app.schemas.comments_schema import CommentResponseModel, CommentCreateRequestModel, \
    CommentUpdateRequestModel

router = APIRouter(tags=["comments"])

@router.get(
    "/api/threads/{thread_id}/comments",
    response_model=ResponseModel[Page[CommentResponseModel]],
    summary="Получение комментариев треда (постранично, старые сверху)",
    description="",
    responses={
        200: {"description": "Страница комментариев треда"},
        404: {"description": "Тред с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_comments(
    thread_id: int,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: CommentService = Depends(get_comment_service)
):
    return await service.get_comments(thread_id=thread_id, limit=limit, offset=offset)

@router.post(
    "/api/threads/{thread_id}/comments",
    response_model=ResponseModel[CommentResponseModel],
    summary="Создание комментария",
    description=(
        "Создание комментария в треде.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными комментария"},
        400: {"description": "Ошибка валидации данных комментария"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Тред с таким id не найден"},
        403: {"description": "Оставлять комментарии могут только участники клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def create_comment(
    thread_id: int,
    model: CommentCreateRequestModel,
    user: DBUser = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    return await service.create_comment(user=user, thread_id=thread_id, model=model)

@router.put(
    "/api/comments/{comment_id}",
    response_model=ResponseModel[CommentResponseModel],
    summary="Редактирование комментария",
    status_code=200,
    responses={
        200: {"description": "Комментарий успешно обновлён"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Комментарий с таким id не найден"},
        403: {"description": "Редактировать комментарий может только автор"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def update_comment(
    comment_id: int,
    model: CommentUpdateRequestModel,
    user: DBUser = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    return await service.update_comment(user=user, comment_id=comment_id, model=model)

@router.delete(
    "/api/comments/{comment_id}",
    response_model=ResponseModel,
    summary="Удаление комментария",
    status_code=200,
    responses={
        200: {"description": "Комментарий успешно удалён"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Комментарий с таким id не найден"},
        403: {"description": "Удалять комментарий может только автор комментария, или владелец клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def delete_comment(
    comment_id: int,
    user: DBUser = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    return await service.delete_comment(user=user, comment_id=comment_id)
