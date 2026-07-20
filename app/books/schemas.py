from typing import Optional

from pydantic import BaseModel, Field

from app.core.schemas import ResponseSchema


class CreateBookRequest(BaseModel):
    """Ручное создание книги (без Google Books)."""
    title: str = Field(min_length=1, max_length=200)
    author: Optional[str] = None
    description: Optional[str] = None
    genres: Optional[str] = None
    published_year: Optional[int] = None


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
