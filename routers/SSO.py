from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.SSO.Models import SingUpRequestModel, SignInRequestModel
from services.SSO.SSOService import SSOService

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post("/signup")
def sign_up(model: SingUpRequestModel, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    :param model: SingUpRequestModel
    :param db: сессия базы данных
    :return: Сообщение об успешной регистрации
    """
    return SSOService.sign_up(model=model, db=db)

@router.post("/signin")
def sign_in(model: SignInRequestModel, db: Session = Depends(get_db)):
    """
    Авторизация пользователя.
    :param model: SignInRequestMode
    :param db: сессия базы данных
    :return: Токен доступа
    """
    return SSOService.sign_in(model=model, db=db)