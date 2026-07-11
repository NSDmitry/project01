from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.genres.repository import GenreRepository
from app.genres.service import GenreService


def get_genre_repository(db: AsyncSession = Depends(get_db)) -> GenreRepository:
    return GenreRepository(db)

def get_genre_service(
    genre_repository: GenreRepository = Depends(get_genre_repository),
) -> GenreService:
    return GenreService(genre_repository=genre_repository)
