from typing import List

from fastapi import APIRouter, Depends

from app.core.models.response_model import ResponseModel
from app.genres.deps import get_genre_service
from app.genres.schemas import CreateGenreRequest, UpdateGenreRequest, GenreResponse
from app.core.contracts import Principal
from app.core.params import PathId
from app.genres.service import GenreService
from app.iam.deps import get_current_user  # identity-провайдер: единственная санкционированная кросс-доменная зависимость

router = APIRouter(prefix="/api/genres", tags=["genres"])


@router.get(
    "",
    response_model=ResponseModel[List[GenreResponse]],
    summary="Список жанров",
    description="Возвращает справочник жанров книжных клубов.\n\n",
    responses={
        200: {"description": "Список жанров"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_genres(
        service: GenreService = Depends(get_genre_service),
) -> ResponseModel[List[GenreResponse]]:
    return await service.list_genres()


@router.post(
    "",
    response_model=ResponseModel[GenreResponse],
    summary="Создание жанра",
    description=(
            "Создаёт новый жанр в справочнике.\n\n"
            "Доступно только администратору.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными жанра"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Доступно только администратору"},
        409: {"description": "Жанр с таким кодом уже существует"},
        422: {"description": "Ошибка валидации"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def create_genre(
        model: CreateGenreRequest,
        user: Principal = Depends(get_current_user),
        service: GenreService = Depends(get_genre_service),
) -> ResponseModel[GenreResponse]:
    return await service.create_genre(user, model)


@router.put(
    "/{genre_id}",
    response_model=ResponseModel[GenreResponse],
    summary="Редактирование жанра",
    description=(
            "Заменяет код, название и порядок сортировки жанра.\n\n"
            "Доступно только администратору.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Модель обновлённого жанра"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Доступно только администратору"},
        404: {"description": "Жанр с таким id не найден"},
        409: {"description": "Жанр с таким кодом уже существует"},
        422: {"description": "Ошибка валидации"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def update_genre(
        genre_id: PathId,
        model: UpdateGenreRequest,
        user: Principal = Depends(get_current_user),
        service: GenreService = Depends(get_genre_service),
) -> ResponseModel[GenreResponse]:
    return await service.update_genre(user, genre_id, model)


@router.delete(
    "/{genre_id}",
    response_model=ResponseModel,
    summary="Удаление жанра",
    description=(
            "Доступно только администратору.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Успешный ответ с сообщением об успешном удалении"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Доступно только администратору"},
        404: {"description": "Жанр с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def delete_genre(
        genre_id: PathId,
        user: Principal = Depends(get_current_user),
        service: GenreService = Depends(get_genre_service),
) -> ResponseModel:
    return await service.delete_genre(user, genre_id)
