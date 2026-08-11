from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.repository import BookClubRepository, NominationRepository, ReadingRepository
from app.bookclubs.service import BookClubService, NominationService, ReadingService
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


# Соседние домены подставляем их репозиториями напрямую - кросс-доменное
# взаимодействие идёт прямыми вызовами. Зависимости на домен тредов нет:
# счётчик тредов клубу правит сам домен тредов вызовом change_threads_count.
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


def get_nomination_repository(db: AsyncSession = Depends(get_db)) -> NominationRepository:
    return NominationRepository(db)


def get_nomination_service(
        nomination_repository: NominationRepository = Depends(get_nomination_repository),
        reading_repository: ReadingRepository = Depends(get_reading_repository),
        book_club_repository: BookClubRepository = Depends(get_club_repository),
        book_service: BookService = Depends(get_book_service),
) -> NominationService:
    return NominationService(
        nomination_repository=nomination_repository,
        reading_repository=reading_repository,
        book_club_repository=book_club_repository,
        book_service=book_service,
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
