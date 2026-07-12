from typing import List

from fastapi import APIRouter, Depends, Query

from app.books.deps import get_book_service
from app.books.schemas import BookSuggestionResponse
from app.books.service import BookService
from app.core.models.response_model import ResponseModel
from app.iam.deps import get_current_user

router = APIRouter(prefix="/api/books", tags=["books"])

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
    },
)
async def search_books(
    q: str = Query(..., min_length=1, max_length=200),
    _user=Depends(get_current_user),
    service: BookService = Depends(get_book_service),
):
    return await service.search_books(q)
