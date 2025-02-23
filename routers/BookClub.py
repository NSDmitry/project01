from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.BookClub.BookClubService import BookClubSerivce
from services.BookClub.Models import CreateBookClubRequestModel
from services.OAuth2PasswordBearer.OAuth2PasswordBearer import oauth2_scheme

router = APIRouter(prefix="/api/bookclubs", tags=["bookclubs"])

@router.post("")
def create(model: CreateBookClubRequestModel, access_token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return BookClubSerivce.create_book_club(model, access_token, db)

@router.get("/owned")
def get_owned_book_clubs(access_token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return BookClubSerivce.get_owned_book_clubs(access_token, db)