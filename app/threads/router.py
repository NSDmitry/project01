from fastapi import APIRouter, Depends, Query

from app.core.contracts import Principal, UserSummary
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.iam.deps import get_current_user, get_optional_user  # identity-провайдер: единственная санкционированная кросс-доменная зависимость
from app.threads.deps import get_thread_service, get_comment_service
from app.threads.schemas import (
    ThreadResponse,
    ThreadCreateRequest,
    ThreadUpdateRequest,
    CommentResponse,
    CommentCreateRequest,
    CommentUpdateRequest,
)
from app.threads.service import ThreadService, CommentService

threads_router = APIRouter(prefix="/api/threads", tags=["threads"])
comments_router = APIRouter(tags=["comments"])


@threads_router.get(
    "/{club_id}",
    response_model=ResponseModel[Page[ThreadResponse]],
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


@threads_router.post(
    "",
    response_model=ResponseModel[ThreadResponse],
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
        model: ThreadCreateRequest,
        user: Principal = Depends(get_current_user),
        service: ThreadService = Depends(get_thread_service)
):
    return await service.create_thread(user=user, model=model)


@threads_router.delete(
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
        user: Principal = Depends(get_current_user),
        service: ThreadService = Depends(get_thread_service)
):
    return await service.delete_thread(user=user, thread_id=thread_id)


@threads_router.put(
    "/{thread_id}",
    response_model=ResponseModel[ThreadResponse],
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
        model: ThreadUpdateRequest,
        user: Principal = Depends(get_current_user),
        service: ThreadService = Depends(get_thread_service)
):
    return await service.update_thread(user=user, thread_id=thread_id, model=model)


@comments_router.get(
    "/api/threads/{thread_id}/comments",
    response_model=ResponseModel[Page[CommentResponse]],
    summary="Получение комментариев треда (постранично, старые сверху)",
    description=(
            "Авторизация не требуется. Если передан заголовок `X-Session-Id`, "
            "поле `is_liked` отражает лайки текущего пользователя.\n\n"
    ),
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
        user: Principal | None = Depends(get_optional_user),
        service: CommentService = Depends(get_comment_service)
):
    return await service.get_comments(thread_id=thread_id, limit=limit, offset=offset, user=user)


@comments_router.post(
    "/api/threads/{thread_id}/comments",
    response_model=ResponseModel[CommentResponse],
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
        model: CommentCreateRequest,
        user: Principal = Depends(get_current_user),
        service: CommentService = Depends(get_comment_service)
):
    return await service.create_comment(user=user, thread_id=thread_id, model=model)


@comments_router.put(
    "/api/comments/{comment_id}",
    response_model=ResponseModel[CommentResponse],
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
        model: CommentUpdateRequest,
        user: Principal = Depends(get_current_user),
        service: CommentService = Depends(get_comment_service)
):
    return await service.update_comment(user=user, comment_id=comment_id, model=model)


@comments_router.delete(
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
        user: Principal = Depends(get_current_user),
        service: CommentService = Depends(get_comment_service)
):
    return await service.delete_comment(user=user, comment_id=comment_id)


@comments_router.get(
    "/api/comments/{comment_id}/likes",
    response_model=ResponseModel[Page[UserSummary]],
    summary="Получение лайкнувших комментарий (постранично, свежие сверху)",
    description="Авторизация не требуется.",
    responses={
        200: {"description": "Страница пользователей, лайкнувших комментарий"},
        404: {"description": "Комментарий с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_comment_likers(
        comment_id: int,
        limit: int = Query(10, ge=1, le=100),
        offset: int = Query(0, ge=0),
        service: CommentService = Depends(get_comment_service)
):
    return await service.get_comment_likers(comment_id=comment_id, limit=limit, offset=offset)


@comments_router.post(
    "/api/comments/{comment_id}/like",
    response_model=ResponseModel[CommentResponse],
    summary="Поставить лайк комментарию",
    description=(
            "Лайк комментария. Идемпотентно - повторный лайк не ошибка.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=200,
    responses={
        200: {"description": "Комментарий с актуальными likes_count и is_liked"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Комментарий с таким id не найден"},
        403: {"description": "Ставить лайки могут только участники клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def like_comment(
        comment_id: int,
        user: Principal = Depends(get_current_user),
        service: CommentService = Depends(get_comment_service)
):
    return await service.like_comment(user=user, comment_id=comment_id)


@comments_router.delete(
    "/api/comments/{comment_id}/like",
    response_model=ResponseModel[CommentResponse],
    summary="Убрать лайк с комментария",
    description=(
            "Снятие своего лайка. Идемпотентно - снятие отсутствующего лайка не ошибка.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=200,
    responses={
        200: {"description": "Комментарий с актуальными likes_count и is_liked"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Комментарий с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def unlike_comment(
        comment_id: int,
        user: Principal = Depends(get_current_user),
        service: CommentService = Depends(get_comment_service)
):
    return await service.unlike_comment(user=user, comment_id=comment_id)
