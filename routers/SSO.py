from sqlite3 import IntegrityError
import uuid
import bcrypt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from DBmodels.DBUser import DBUser
from models.User import User
from models.requests.SignInRequest import SignInRequest
from models.responses.SignInReposponse import SignInResponse

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post("/signup")
def registration(user: User, db: Session = Depends(get_db)):
    """
    API-метод для создания пользователя.
    Ожидает JSON с полями: id, name, email, password.
    """

    hashed_password = hash_password(user.password)
    user_model = DBUser(
        name=user.name,
        phone_number=user.phone_number,
        password=hashed_password,
        access_token=str(uuid.uuid4())
    )

    try:
        db.add(user_model)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="Пользователь с таким номером уже существует")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка запроса")

    return {
        "message": "Пользователь успешно зарегистрирован"
    }

@router.post("/signin", response_model=SignInResponse)
def signin(credentials: SignInRequest, db: Session=Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.phone_number == credentials.phone_number).first()

    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="Пользователь с таким номером телефона не найден"
        )

    if verify_password_bcrypt(credentials.password, db_user.password) is False:
        raise HTTPException(
            status_code=401,
            detail="Пароь не правильный",
        )

    return SignInResponse(
        message="Авторизация успешна",
        access_token=db_user.access_token
    )

def verify_password_bcrypt(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)

    return hashed.decode('utf-8')