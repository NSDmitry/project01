from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book
from app.books.schemas import BookSuggestionResponse


class BookRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_volume_id(self, volume_id: str) -> Optional[Book]:
        result = await self.db.execute(
            select(Book).where(Book.google_volume_id == volume_id)
        )

        return result.scalar_one_or_none()

    async def create(self, data: BookSuggestionResponse) -> Book:
        book = Book(
            google_volume_id=data.volume_id,
            title=data.title,
            author=data.author,
            description=data.description,
            genres=data.genres,
            published_year=data.published_year,
        )
        self.db.add(book)
        await self.db.flush()

        return book
