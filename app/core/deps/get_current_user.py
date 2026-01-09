from fastapi import Security
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.deps.deps import get_user_repository
from app.db.models.db_user import DBUser
from app.db.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(
        token: str = Security(oauth2_scheme),
        user_repository: UserRepository = Depends(get_user_repository)) -> DBUser:

    return user_repository.get_user_by_access_token(token)