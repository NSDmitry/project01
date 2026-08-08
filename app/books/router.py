from typing import List

from fastapi import APIRouter, Depends, Query

from app.books.deps import get_book_service
from app.books.schemas import BookResponse, BookSuggestionResponse, CreateBookRequest
from app.books.service import BookService
from app.core.contracts import Principal
from app.core.models.response_model import ResponseModel
from app.iam.deps import get_current_user

router = APIRouter(prefix="/api/books", tags=["books"])

@router.post(
    "",
    response_model=ResponseModel[BookResponse],
    summary="Ручное создание книги",
    description=(
        "Создание книги вручную, без привязки к Google Books.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными созданной книги"},
        422: {"description": "Ошибка валидации (отсутствует или пустое название)"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def create_book(
    model: CreateBookRequest,
    _user: Principal = Depends(get_current_user),
    service: BookService = Depends(get_book_service),
) -> ResponseModel[BookResponse]:
    return await service.create_book(model)


@router.get(
    "/search",
    response_model=ResponseModel[List[BookSuggestionResponse]],
    summary="Поиск книг в Google Books (подсказки для автокомплита)",
    description=(
        "Поиск книг по названию через Google Books API. Ничего не сохраняет в БД.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Список найденных книг"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
        503: {"description": "Google Books временно недоступен"},
    },
)
async def search_books(
    q: str = Query(..., min_length=1, max_length=200),
    _user: Principal = Depends(get_current_user),
    service: BookService = Depends(get_book_service),
) -> ResponseModel[List[BookSuggestionResponse]]:
    return await service.search_books(q)
