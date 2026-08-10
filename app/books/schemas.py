from typing import Optional

from pydantic import BaseModel, Field

from app.core.contracts import BookResponse  # noqa: F401 - контракт живёт в core, ре-экспорт для домена


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
    cover_url: Optional[str] = None
    page_count: Optional[int] = None
