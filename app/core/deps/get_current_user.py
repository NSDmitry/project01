from fastapi import Security
from fastapi.params import Depends
from fastapi.security import APIKeyHeader

from app.api.services.user_session_service import UserSessionService
from app.core.deps.deps import get_user_repository, get_user_session_service
from app.core.errors.errors import Unauthorized
from app.db.models.db_user import DBUser
from app.db.repositories.user_repository import UserRepository

session_header = APIKeyHeader(name="X-Session-Id", auto_error=False)

def get_current_user(
    sid: str | None = Security(session_header),
    user_repository: UserRepository = Depends(get_user_repository),
    user_session_service: UserSessionService = Depends(get_user_session_service)
) -> DBUser:

    if not sid:
        raise Unauthorized(errors=["Missing session"])

    user_session = user_session_service.get_user_session(sid)

    if not user_session:
        raise Unauthorized(errors=["Invalid session"])

    return user_repository.get_user_by_id(user_session.user_id)