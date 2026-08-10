from fastapi import APIRouter, Depends, Query

from app.bookclubs.deps import get_book_club_service
from app.bookclubs.schemas import (
    CreateBookClubRequest,
    UpdateBookClubGenresRequest,
    UpdateBookClubRequest,
    SearchBookClubsRequest,
    BookClubResponse,
)
from app.bookclubs.service import BookClubService
from app.core.contracts import Principal, UserSummary
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.core.params import PageOffset, PathId
from app.iam.deps import get_current_user  # identity-провайдер: единственная санкционированная кросс-доменная зависимость

router = APIRouter(prefix="/api/bookclubs", tags=["bookclubs"])


@router.post(
    "",
    response_model=ResponseModel[BookClubResponse],
    summary="Создание книжного клуба",
    description=(
            "Создание книжного клуба.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными книжного клуба"},
        422: {"description": "Ошибка валидации названия, описания или жанров книжного клуба"},
        409: {"description": "Клуб с таким названием уже существует"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def create(
        model: CreateBookClubRequest,
        user: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[BookClubResponse]:
    return await service.create_book_club(model, user)


@router.get(
    "",
    response_model=ResponseModel[Page[BookClubResponse]],
    summary="Получение книжных клубов (постранично)",
    description=(
            "Возвращает все книжные клубы постранично.\n\n"
            "Для поиска по названию, описанию и жанрам используйте `POST /api/bookclubs/search`.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Страница книжных клубов"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_all_book_clubs(
        limit: int = Query(20, ge=1, le=100),
        offset: PageOffset = 0,
        _: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[Page[BookClubResponse]]:
    return await service.get_book_clubs(limit, offset)


@router.post(
    "/search",
    response_model=ResponseModel[Page[BookClubResponse]],
    summary="Поиск книжных клубов",
    description=(
            "Постраничный полнотекстовый поиск клубов по названию и описанию. "
            "Регистр и словоформы не важны (`фантаст` найдёт `фантастические`), "
            "слово можно не дописывать - оно ищется по началу. Результаты "
            "отсортированы по релевантности, совпадение в названии весит больше.\n\n"
            "Поле `genres` - фильтр по кодам жанров, сужающий выдачу: клуб должен "
            "иметь хотя бы один из перечисленных жанров. С `query` совмещается по И.\n\n"
            "Поле `relation` ограничивает выборку клубами текущего пользователя:\n"
            "- `owner` - клубы, где пользователь владелец;\n"
            "- `member` - клубы, в которых пользователь состоит (включая собственные).\n\n"
            "Все поля необязательны: пустой запрос вернёт все клубы постранично.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Страница найденных книжных клубов"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        422: {"description": "Ошибка валидации параметров поиска"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def search_book_clubs(
        model: SearchBookClubsRequest,
        user: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[Page[BookClubResponse]]:
    return await service.search_book_clubs(user, model)


@router.get(
    "/{club_id}",
    response_model=ResponseModel[BookClubResponse],
    summary="Получение книжного клуба по id",
    description=(
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Успешный ответ с данными книжного клуба"},
        404: {"description": "Книжный клуб с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def get_book_club(
        club_id: PathId,
        _: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[BookClubResponse]:
    return await service.get_book_club(club_id)


@router.get(
    "/{club_id}/members",
    response_model=ResponseModel[Page[UserSummary]],
    summary="Получение участников книжного клуба (постранично)",
    description=(
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Страница участников клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_book_club_members(
        club_id: PathId,
        limit: int = Query(20, ge=1, le=100),
        offset: PageOffset = 0,
        _: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[Page[UserSummary]]:
    return await service.get_members(club_id, limit=limit, offset=offset)


@router.delete(
    "/{club_id}",
    response_model=ResponseModel,
    summary="Удаление книжного клуба",
    description=(
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Успешный ответ с сообщением об успешном удалении"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Пользователь не является владельцем книжного клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def delete_book_club(
        club_id: PathId,
        user: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel:
    return await service.delete_book_club(user, club_id)


@router.post(
    "/{club_id}/join",
    response_model=ResponseModel[BookClubResponse],
    summary="Вступить в книжный клуб",
    description=(
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Модель измененного книжного клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб с таким id не найден"},
        409: {"description": "Пользователь уже является участником клуба"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def join(
        club_id: PathId,
        user: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[BookClubResponse]:
    return await service.join(user, club_id)


@router.delete(
    "/{club_id}/leave",
    response_model=ResponseModel[BookClubResponse],
    summary="Выйти из участников клуба",
    description=(
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Модель измененного книжного клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        409: {"description": "Пользователь не состоит в клубе"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def leave(
        club_id: PathId,
        user: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[BookClubResponse]:
    return await service.leave(user, club_id)


@router.put(
    "/{club_id}/genres",
    response_model=ResponseModel[BookClubResponse],
    summary="Обновление жанров книжного клуба",
    description=(
            "Заменяет набор жанров клуба присланным списком кодов (от 0 до 5).\n\n"
            "Доступно только владельцу клуба.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Модель книжного клуба с обновлёнными жанрами"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Пользователь не является владельцем книжного клуба"},
        404: {"description": "Книжный клуб с таким id не найден"},
        422: {"description": "Некорректный или неизвестный жанр"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def set_genres(
        club_id: PathId,
        model: UpdateBookClubGenresRequest,
        user: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[BookClubResponse]:
    return await service.set_genres(user, club_id, model)


@router.patch(
    "/{club_id}",
    response_model=ResponseModel[BookClubResponse],
    summary="Обновление информации о книжном клубе",
    description=(
            "Обновляет название и/или описание клуба: присланные поля заменяются, "
            "отсутствующие остаются без изменений.\n\n"
            "Доступно только владельцу клуба.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Модель книжного клуба с обновлёнными полями"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Пользователь не является владельцем книжного клуба"},
        404: {"description": "Книжный клуб с таким id не найден"},
        409: {"description": "Книжный клуб с таким названием уже существует"},
        422: {"description": "Некорректные данные для обновления"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def update_book_club(
        club_id: PathId,
        model: UpdateBookClubRequest,
        user: Principal = Depends(get_current_user),
        service: BookClubService = Depends(get_book_club_service)
) -> ResponseModel[BookClubResponse]:
    return await service.update_book_club(user, club_id, model)
