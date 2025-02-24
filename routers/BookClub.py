from fastapi import APIRouter, Depends

from services.BookClub.BookClubService import BookClubSerivce
from services.BookClub.Models import CreateBookClubRequestModel
from services.OAuth2PasswordBearer.OAuth2PasswordBearer import oauth2_scheme

router = APIRouter(prefix="/api/bookclubs", tags=["bookclubs"])

@router.post("")
def create(model: CreateBookClubRequestModel, access_token: str = Depends(oauth2_scheme), service: BookClubSerivce = Depends()):
    return service.create_book_club(model, access_token)

@router.get("")
def get_all_book_clubs(service: BookClubSerivce = Depends()):
    return service.get_book_clubs()

@router.get("/owned")
def get_owned_book_clubs(access_token: str = Depends(oauth2_scheme), service: BookClubSerivce = Depends()):
    return service.get_owned_book_clubs(access_token)

@router.delete("/{club_id}")
def delete_book_club(club_id: int, access_token: str = Depends(oauth2_scheme), service: BookClubSerivce = Depends()):
    return service.delete_book_club(access_token, club_id)