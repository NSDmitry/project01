from fastapi import Security
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from app.db.models.db_user import DBUser
from app.db.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(
        token: str = Security(oauth2_scheme),
        user_service: UserRepository = Depends()) -> DBUser:

    return user_service.get_user_by_access_token(token)