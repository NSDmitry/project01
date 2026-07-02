from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.thread_repository import ThreadRepository

from app.api.services.user_service import UserService
from app.api.services.book_club_service import BookClubService
from app.api.services.thread_service import ThreadService
from app.api.services.auth_service import AuthService
from app.db.repositories.user_session_repository import UserSessionRepository
from app.api.services.user_session_service import UserSessionService
from app.settings import settings


######## repositories ########

def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_club_repository(db: AsyncSession = Depends(get_db)) -> BookClubRepository:
    return BookClubRepository(db)

def get_thread_repository(db: AsyncSession = Depends(get_db)) -> ThreadRepository:
    return ThreadRepository(db)

def get_user_session_repository(db: AsyncSession = Depends(get_db)) -> UserSessionRepository:
    return UserSessionRepository(db)


######## services ########

def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(user_repository=user_repository)

def get_book_club_service(
    user_repository: UserRepository = Depends(get_user_repository),
    book_club_repository: BookClubRepository = Depends(get_club_repository),
) -> BookClubService:
    return BookClubService(
        user_repository=user_repository,
        book_club_repository=book_club_repository,
    )

def get_thread_service(
    thread_repository: ThreadRepository = Depends(get_thread_repository),
    book_club_repository: BookClubRepository = Depends(get_club_repository),
) -> ThreadService:
    return ThreadService(
        thread_repository=thread_repository,
        book_club_repository=book_club_repository,
    )

def get_user_session_service(
    user_session_repository: UserSessionRepository = Depends(get_user_session_repository),
) -> UserSessionService:
    return UserSessionService(user_session_repository=user_session_repository)

def get_auth_service(
    user_service: UserService = Depends(get_user_service),
    user_repository: UserRepository = Depends(get_user_repository),
    user_session_service: UserSessionService = Depends(get_user_session_service),
) -> AuthService:
    return AuthService(
        user_service=user_service,
        user_repository=user_repository,
        user_session_service=user_session_service,
        telegram_bot_token=settings.telegram_bot_token,
    )