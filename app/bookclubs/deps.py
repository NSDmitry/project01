from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.repository import BookClubRepository
from app.bookclubs.service import BookClubService
from app.core.database import get_db
from app.iam.deps import get_user_repository
from app.iam.repository import UserRepository


def get_club_repository(db: AsyncSession = Depends(get_db)) -> BookClubRepository:
    return BookClubRepository(db)

def get_book_club_service(
    user_repository: UserRepository = Depends(get_user_repository),
    book_club_repository: BookClubRepository = Depends(get_club_repository),
) -> BookClubService:
    return BookClubService(
        user_repository=user_repository,
        book_club_repository=book_club_repository,
    )
