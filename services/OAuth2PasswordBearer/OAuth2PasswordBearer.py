from fastapi import Security, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from DBmodels import DBUser
from database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Security(oauth2_scheme), db: Session = Depends(get_db)) -> DBUser:
    user = db.query(DBUser).filter(DBUser.access_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user