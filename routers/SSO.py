import uuid
from sqlite3 import IntegrityError

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from DBmodels.DBUser import DBUser
from database import get_db
from models.User import User
from models.requests.SignInRequest import SignInRequest
from models.responses.SignInReposponse import SignInResponse
from services.SSOService import SSOService

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post("/signup")
def registration(user: User, db: Session = Depends(get_db)):
    return SSOService.register_user(user, db)

@router.post("/signin", response_model=SignInResponse)
def signin(credentials: SignInRequest, db: Session=Depends(get_db)):
    return SSOService.signin_user(credentials, db)