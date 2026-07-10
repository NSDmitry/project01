from typing import List

from fastapi import APIRouter, Depends, Query

from app.bookclubs.deps import get_book_club_service
from app.bookclubs.schemas import (
    CreateBookClubRequest,
    UpdateBookClubGenresRequest,
    BookClubResponse,
    BookClubRelation,
    GenreResponse,
)
from app.bookclubs.service import BookClubService
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.iam.deps import get_current_user
from app.iam.models import User
from app.iam.schemas import UserSummary

router = APIRouter(prefix="/api/bookclubs", tags=["bookclubs"])

@router.post(
    "",
    response_model=ResponseModel[BookClubResponse],
    summary="Создание книжного клуба",
    description=(
        "Создание книжного клуба.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными книжного клуба"},
        422: {"description": "Ошибка валидации названия, описания или жанров книжного клуба"},
        409: {"description": "Клуб с таким названием уже существует"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def create(
        model: CreateBookClubRequest,
        user: User = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
):
    response: BookClubResponse = await service.create_book_club(model, user)

    return response

@router.get(
    "",
    response_model=ResponseModel[List[BookClubResponse]],
    summary="Получение книжных клубов",
    description=(
        "Возвращает книжные клубы. По умолчанию - все клубы.\n\n"
        "Параметр `relation` ограничивает выборку клубами текущего пользователя:\n"
        "- `owner` - клубы, где пользователь владелец;\n"
        "- `member` - клубы, в которых пользователь состоит (включая собственные).\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Успешный ответ с данными книжных клубов"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_all_book_clubs(
    relation: BookClubRelation | None = Query(
        None,
        description="Фильтр по связи с текущим пользователем: owner или member",
    ),
    user: User = Depends(get_current_user),
    service: BookClubService = Depends(get_book_club_service)
):
    return await service.get_book_clubs(user, relation)

@router.get(
    "/genres",
    response_model=ResponseModel[List[GenreResponse]],
    summary="Список доступных жанров",
    description=(
        "Возвращает справочник активных жанров книжных клубов.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Список доступных жанров"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_genres(
    _: User = Depends(get_current_user),
    service: BookClubService = Depends(get_book_club_service),
):
    return await service.list_genres()

@router.get(
    "/{club_id}",
    response_model=ResponseModel[BookClubResponse],
    summary="Получение книжного клуба по id",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses = {
        200: {"description": "Успешный ответ с данными книжного клуба"},
        404: {"description": "Книжный клуб с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def get_book_club(
    club_id: int,
    _: User = Depends(get_current_user),
    service: BookClubService = Depends(get_book_club_service)
):
    return await service.get_book_club(club_id)

@router.get(
    "/{club_id}/members",
    response_model=ResponseModel[Page[UserSummary]],
    summary="Получение участников книжного клуба (постранично)",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Страница участников клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_book_club_members(
    club_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    service: BookClubService = Depends(get_book_club_service)
):
    return await service.get_members(club_id, limit=limit, offset=offset)

@router.delete(
    "/{club_id}",
    response_model=ResponseModel,
    summary="Удаление книжного клуба",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Успешный ответ с сообщением об успешном удалении"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Пользователь не является владельцем книжного клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def delete_book_club(
    club_id: int,
    user: User = Depends(get_current_user),
    service: BookClubService = Depends(get_book_club_service)
):
    return await service.delete_book_club(user, club_id)

@router.post(
    "/{club_id}/join",
    response_model=ResponseModel[BookClubResponse],
    summary="Вступить в книжный клуб",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Модель измененного книжного клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def join(
    club_id: int,
    user: User = Depends(get_current_user),
    service: BookClubService = Depends(get_book_club_service)
):
    return await service.join(user, club_id)

@router.delete(
    "/{club_id}/leave",
    response_model=ResponseModel[BookClubResponse],
    summary="Выйти из участников клуба",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Модель измененного книжного клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Пользователь не участник клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def leave(
    club_id: int,
    user: User = Depends(get_current_user),
    service: BookClubService = Depends(get_book_club_service)
):
    return await service.leave(user, club_id)

@router.put(
    "/{club_id}/genres",
    response_model=ResponseModel[BookClubResponse],
    summary="Обновление жанров книжного клуба",
    description=(
        "Заменяет набор жанров клуба присланным списком кодов (от 1 до 5).\n\n"
        "Доступно только владельцу клуба.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Модель книжного клуба с обновлёнными жанрами"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Пользователь не является владельцем книжного клуба"},
        404: {"description": "Книжный клуб с таким id не найден"},
        422: {"description": "Некорректный или неизвестный жанр"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def set_genres(
    club_id: int,
    model: UpdateBookClubGenresRequest,
    user: User = Depends(get_current_user),
    service: BookClubService = Depends(get_book_club_service)
):
    return await service.set_genres(user, club_id, model)
