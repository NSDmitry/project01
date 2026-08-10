from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.repository import BookClubRepository, ReadingRepository
from app.bookclubs.service import BookClubService, ReadingService
from app.books.deps import get_book_service
from app.books.service import BookService
from app.core.database import get_db
from app.genres.deps import get_genre_repository
from app.genres.repository import GenreRepository
from app.iam.deps import get_user_repository
from app.iam.repository import UserRepository


def get_club_repository(db: AsyncSession = Depends(get_db)) -> BookClubRepository:
    return BookClubRepository(db)


def get_reading_repository(db: AsyncSession = Depends(get_db)) -> ReadingRepository:
    return ReadingRepository(db)


# Соседние домены подставляем их репозиториями (реализуют порты клубов). После
# распила здесь окажутся HTTP-клиенты. threads больше нет: счётчик тредов клуб
# ведёт сам по событиям, обратной зависимости на домен тредов не осталось.
def get_book_club_service(
        book_club_repository: BookClubRepository = Depends(get_club_repository),
        reading_repository: ReadingRepository = Depends(get_reading_repository),
        genre_repository: GenreRepository = Depends(get_genre_repository),
        user_repository: UserRepository = Depends(get_user_repository),
) -> BookClubService:
    return BookClubService(
        book_club_repository=book_club_repository,
        reading_repository=reading_repository,
        genre_repository=genre_repository,
        user_repository=user_repository,
    )


def get_reading_service(
        reading_repository: ReadingRepository = Depends(get_reading_repository),
        book_club_repository: BookClubRepository = Depends(get_club_repository),
        book_service: BookService = Depends(get_book_service),
        user_repository: UserRepository = Depends(get_user_repository),
) -> ReadingService:
    return ReadingService(
        reading_repository=reading_repository,
        book_club_repository=book_club_repository,
        book_service=book_service,
        user_repository=user_repository,
    )
