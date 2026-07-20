from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.repository import BookClubRepository
from app.core.database import get_db
from app.core.errors.errors import NotFound, Unauthorized
from app.iam.models import User
from app.iam.repository import UserRepository, UserSessionRepository
from app.iam.service import AuthService, UserService, UserSessionService
from app.settings import settings


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_user_session_repository(db: AsyncSession = Depends(get_db)) -> UserSessionRepository:
    return UserSessionRepository(db)

def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(user_repository=user_repository)

def get_user_session_service(
    user_session_repository: UserSessionRepository = Depends(get_user_session_repository),
) -> UserSessionService:
    return UserSessionService(user_session_repository=user_session_repository)

# BookClubRepository создаём напрямую от db, а не через app.bookclubs.deps -
# иначе получился бы циклический импорт (bookclubs.deps импортирует iam.deps).
def get_auth_service(
    user_service: UserService = Depends(get_user_service),
    user_repository: UserRepository = Depends(get_user_repository),
    user_session_service: UserSessionService = Depends(get_user_session_service),
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    return AuthService(
        user_service=user_service,
        user_repository=user_repository,
        user_session_service=user_session_service,
        book_club_repository=BookClubRepository(db),
        telegram_bot_token=settings.telegram_bot_token,
    )


session_header = APIKeyHeader(name="X-Session-Id", auto_error=False)

async def get_current_user(
    sid: str | None = Security(session_header),
    user_repository: UserRepository = Depends(get_user_repository),
    user_session_service: UserSessionService = Depends(get_user_session_service)
) -> User:

    if not sid:
        raise Unauthorized(errors=["Missing session"])

    user_session = await user_session_service.get_user_session(sid)

    if not user_session:
        raise Unauthorized(errors=["Invalid session"])

    try:
        return await user_repository.get_user_by_id(user_session.user_id)
    except NotFound:
        # Сессия без живого пользователя (у user_sessions.user_id нет FK) - это сбой
        # авторизации, а не отсутствие ресурса
        raise Unauthorized(errors=["Invalid session"])


async def get_optional_user(
    sid: str | None = Security(session_header),
    user_repository: UserRepository = Depends(get_user_repository),
    user_session_service: UserSessionService = Depends(get_user_session_service)
) -> User | None:
    """Как get_current_user, но любой сбой авторизации - анонимный доступ, а не ошибка."""
    try:
        return await get_current_user(sid, user_repository, user_session_service)
    except (Unauthorized, NotFound):
        return None
