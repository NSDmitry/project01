from typing import List

from fastapi import APIRouter, Depends

from services.BookClub.BookClubService import BookClubSerivce
from services.BookClub.Models import CreateBookClubRequestModel, BookClubResponseModel, DeleteBookClubResponse
from services.OAuth2PasswordBearer.OAuth2PasswordBearer import oauth2_scheme

router = APIRouter(prefix="/api/bookclubs", tags=["bookclubs"])

@router.post(
    "",
    response_model=BookClubResponseModel,
    summary="Создание книжного клуба",
    description=(
        "Создание книжного клуба.\n\n"
        "**Требуется авторизация** с заголовком:\n"
        "`Authorization: Bearer <your_token>`\n\n"
    ),
    responses={
        201: {"description": "Успешный ответ с данными книжного клуба"},
        400: {"description": "Ошибка валидации названия или описания книжного клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
def create(model: CreateBookClubRequestModel, access_token: str = Depends(oauth2_scheme), service: BookClubSerivce = Depends()):
    response: BookClubResponseModel = service.create_book_club(model, access_token)

    return response



@router.get(
    "",
    response_model=List[BookClubResponseModel],
    summary="Получение всех книжных клубов",
    responses={
        200: {"description": "Успешный ответ с данными книжных клубов"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
def get_all_book_clubs(service: BookClubSerivce = Depends()):
    response: List[BookClubResponseModel] = service.get_book_clubs()

    return response

@router.get(
    "/owned",
    response_model=List[BookClubResponseModel],
    summary="Получение всех книжных клубов, в которых пользователь владелец",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`Authorization: Bearer <your_token>`\n\n"
    ),
    responses={
        200: {"description": "Успешный ответ с данными книжных клубов"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
def get_owned_book_clubs(access_token: str = Depends(oauth2_scheme), service: BookClubSerivce = Depends()):
    response: List[BookClubResponseModel] = service.get_owned_book_clubs(access_token)

    return response

@router.delete(
    "/{club_id}",
    response_model=DeleteBookClubResponse,
    summary="Удаление книжного клуба",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`Authorization: Bearer <your_token>`\n\n"
    ),
    responses={
        200: {"description": "Успешный ответ с сообщением об успешном удалении"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
def delete_book_club(club_id: int, access_token: str = Depends(oauth2_scheme), service: BookClubSerivce = Depends()):
    response: DeleteBookClubResponse = service.delete_book_club(access_token, club_id)

    return response

@router.post(
    "/{club_id}/join",
    response_model=BookClubResponseModel,
    summary="Вступить в книжный клуб",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`Authorization: Bearer <your_token>`\n\n"
    ),
    responses={
        200: {"description": "Модель измененного книжного клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
def join(club_id: int, access_token: str = Depends(oauth2_scheme), service: BookClubSerivce = Depends()):
    return service.join(access_token, club_id)

@router.delete(
    "/{club_id}/leave",
    response_model=BookClubResponseModel,
    summary="Выйти из участников клуба",
    description=(
        "**Требуется авторизация** с заголовком:\n"
        "`Authorization: Bearer <your_token>`\n\n"
    ),
    responses={
        200: {"description": "Модель измененного книжного клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Пользователь не участник клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
def join(club_id: int, access_token: str = Depends(oauth2_scheme), service: BookClubSerivce = Depends()):
    return service.leave(access_token, club_id)