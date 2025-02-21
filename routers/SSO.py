from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.SSOService import SSOService

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post("/signup")
def registration(name: str, phone_number: str, password: str, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    :param name: имя пользователя
    :param phone_number: номер телефона
    :param password: пароль пользователя
    :param db: сессия базы данных
    :return: Сообщение об успешной регистрации
    """
    return SSOService.register_user(name=name, phone_number=phone_number, password=password, db=db)

@router.post("/signin")
def signin(phone_number: str, password: str, db: Session = Depends(get_db)):
    """
    Авторизация пользователя.
    :param phone_number: номер телефона
    :param password: пароль пользователя
    :param db: сессия базы данных
    :return: Токен доступа
    """
    return SSOService.signin_user(phone_number=phone_number, password=password, db=db)