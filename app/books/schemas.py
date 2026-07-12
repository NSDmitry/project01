from typing import Optional

from pydantic import BaseModel

from app.core.schemas import ResponseSchema


class BookSuggestionResponse(BaseModel):
    """Книга из результатов поиска Google Books (в БД не сохранена)."""
    volume_id: str
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    genres: Optional[str] = None
    published_year: Optional[int] = None


class BookResponse(ResponseSchema):
    id: int
    # None - книга создана пользователем вручную, без Google Books.
    google_volume_id: Optional[str] = None
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    genres: Optional[str] = None
    published_year: Optional[int] = None
