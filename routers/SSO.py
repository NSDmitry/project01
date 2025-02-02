from http.client import HTTPException
from sqlite3 import IntegrityError
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from DBmodels.DBUser import DBUser
from models.User import User

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post("/")
def registration(user: User, db: Session = Depends(get_db)):
    """
    API-метод для создания пользователя.
    Ожидает JSON с полями: id, name, email, password.
    """

    user_model = DBUser(
        name=user.name,
        phone_number=user.phone_number,
        password=user.password,
        access_token=str(uuid.uuid4())
    )

    try:
        db.add(user_model)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="Пользователь с таким номером уже существует")(e)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка запроса")

    return {
        "message": "Пользователь успешно зарегистрирован"
    }