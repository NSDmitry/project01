from fastapi import Security, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.db_user import DBUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Security(oauth2_scheme), db: Session = get_db()) -> DBUser:
    user = db.query(DBUser).filter(DBUser.access_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user