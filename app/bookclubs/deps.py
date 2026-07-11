from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.repository import BookClubRepository
from app.bookclubs.service import BookClubService
from app.core.database import get_db
from app.genres.deps import get_genre_repository
from app.genres.repository import GenreRepository


def get_club_repository(db: AsyncSession = Depends(get_db)) -> BookClubRepository:
    return BookClubRepository(db)

def get_book_club_service(
    book_club_repository: BookClubRepository = Depends(get_club_repository),
    genre_repository: GenreRepository = Depends(get_genre_repository),
) -> BookClubService:
    return BookClubService(
        book_club_repository=book_club_repository,
        genre_repository=genre_repository,
    )
