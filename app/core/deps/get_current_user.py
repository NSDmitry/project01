from fastapi import Security
from fastapi.params import Depends
from fastapi.security import APIKeyHeader
from fastapi.security.http import HTTPBase, HTTPAuthorizationCredentials

from app.core.deps.deps import get_user_repository
from app.core.errors.errors import Unauthorized
from app.db.models.db_user import DBUser
from app.db.repositories.user_repository import UserRepository

session_header = APIKeyHeader(name="X-Session-Id", auto_error=False)

def get_current_user(
    sid: str | None = Security(session_header),
    user_repository: UserRepository = Depends(get_user_repository)
) -> DBUser:

    if not sid:
        raise Unauthorized(errors=["Missing session"])

    return user_repository.get_user_by_access_token(sid)