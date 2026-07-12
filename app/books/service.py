from typing import List

from app.books.google_client import GoogleBooksClient
from app.books.models import Book
from app.books.repository import BookRepository
from app.books.schemas import BookSuggestionResponse
from app.core.errors.errors import NotFound
from app.core.models.response_model import ResponseModel


class BookService:
    book_repository: BookRepository
    google_client: GoogleBooksClient

    def __init__(self, book_repository: BookRepository, google_client: GoogleBooksClient) -> None:
        self.book_repository = book_repository
        self.google_client = google_client

    async def search_books(self, query: str) -> ResponseModel[List[BookSuggestionResponse]]:
        books = await self.google_client.search(query)

        return ResponseModel.ok(books)

    async def get_or_create_book(self, volume_id: str) -> Book:
        """Вернуть книгу из БД по volume_id, при отсутствии - дотянуть из Google и сохранить."""
        book = await self.book_repository.get_by_volume_id(volume_id)
        if book:
            return book

        data = await self.google_client.get_volume(volume_id)
        if data is None:
            raise NotFound(errors=["Книга с таким id не найдена"])

        return await self.book_repository.create(data)
