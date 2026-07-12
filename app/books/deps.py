from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.google_client import GoogleBooksClient
from app.books.repository import BookRepository
from app.books.service import BookService
from app.core.database import get_db
from app.settings import settings


def get_google_books_client() -> GoogleBooksClient:
    return GoogleBooksClient(api_key=settings.google_books_api_key)

def get_book_repository(db: AsyncSession = Depends(get_db)) -> BookRepository:
    return BookRepository(db)

def get_book_service(
    book_repository: BookRepository = Depends(get_book_repository),
    google_client: GoogleBooksClient = Depends(get_google_books_client),
) -> BookService:
    return BookService(book_repository=book_repository, google_client=google_client)
