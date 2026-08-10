from fastapi import APIRouter, Depends, Query

from app.bookclubs.deps import get_book_club_service, get_nomination_service, get_reading_service
from app.bookclubs.schemas import (
    CreateBookClubRequest,
    CreateNominationRequest,
    CreateReadingRequest,
    CurrentReadingResponse,
    NominationResponse,
    ReadingProgressResponse,
    ReadingResponse,
    ReadingScheduleRequest,
    UpdateBookClubGenresRequest,
    UpdateBookClubRequest,
    UpdateReadingProgressRequest,
    SearchBookClubsRequest,
    BookClubResponse,
)
from app.bookclubs.service import BookClubService, NominationService, ReadingService
from app.core.contracts import Principal, UserSummary
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.core.params import PageOffset, PathId
from app.iam.deps import get_current_user  # identity-провайдер: единственная санкционированная кросс-доменная зависимость

router = APIRouter(prefix="/api/bookclubs", tags=["bookclubs"])
# Заходы клуба адресуются и через клуб (создание, текущий, архив), и напрямую по
# своему id (прогресс, закрытие) - отсюда второй роутер со своим префиксом.
readings_router = APIRouter(prefix="/api/readings", tags=["readings"])
# Голос отдаётся за номинацию - клуб в пути не нужен, он известен по ней самой.
nominations_router = APIRouter(prefix="/api/nominations", tags=["nominations"])


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


@router.post(
    "/{club_id}/readings",
    response_model=ResponseModel[ReadingResponse],
    summary="Создание захода клуба",
    description=(
            "Заводит совместное чтение: книга (по `book_volume_id` из поиска книг), "
            "дата старта, дедлайн и список этапов - частей книги со своими датами. "
            "У этапа можно указать `end_page`, тогда прогресс участника, отмеченный "
            "номером страницы, сам сопоставится с этапом.\n\n"
            "Доступно только владельцу клуба. Незакрытый заход у клуба может быть "
            "только один.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными захода"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Пользователь не является владельцем книжного клуба"},
        404: {"description": "Книжный клуб или книга с таким id не найдены"},
        409: {"description": "У клуба уже есть текущий заход"},
        422: {"description": "Ошибка валидации сроков или этапов"},
        503: {"description": "Google Books временно недоступен"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def create_reading(
        club_id: PathId,
        model: CreateReadingRequest,
        user: Principal = Depends(get_current_user),
        service: ReadingService = Depends(get_reading_service)
) -> ResponseModel[ReadingResponse]:
    return await service.create_reading(user, club_id, model)


@router.get(
    "/{club_id}/readings/current",
    response_model=ResponseModel[CurrentReadingResponse],
    summary="Текущий заход клуба со сводкой прогресса",
    description=(
            "Возвращает незакрытый заход клуба с этапами и сводкой: сколько участников "
            "в графике и какой этап должен быть закрыт к сегодняшнему дню "
            "(`current_stage`). Пока срок первого этапа не наступил, в графике "
            "считаются все участники.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Текущий заход и сводка прогресса"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб не найден или у клуба нет текущего захода"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_current_reading(
        club_id: PathId,
        _: Principal = Depends(get_current_user),
        service: ReadingService = Depends(get_reading_service)
) -> ResponseModel[CurrentReadingResponse]:
    return await service.get_current_reading(club_id)


@router.get(
    "/{club_id}/readings",
    response_model=ResponseModel[Page[ReadingResponse]],
    summary="Архив заходов клуба (постранично, свежие сверху)",
    description=(
            "Все заходы клуба, включая текущий - у него `finished_at` пустой.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Страница заходов клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_readings(
        club_id: PathId,
        limit: int = Query(20, ge=1, le=100),
        offset: PageOffset = 0,
        _: Principal = Depends(get_current_user),
        service: ReadingService = Depends(get_reading_service)
) -> ResponseModel[Page[ReadingResponse]]:
    return await service.get_readings(club_id, limit=limit, offset=offset)


@router.post(
    "/{club_id}/nominations",
    response_model=ResponseModel[NominationResponse],
    summary="Номинировать книгу на следующий заход",
    description=(
            "Предлагает книгу (по `book_volume_id` из поиска книг) кандидатом на "
            "следующее совместное чтение. Доступно участникам клуба.\n\n"
            "Одна и та же книга номинируется в клубе один раз - повторная "
            "номинация отклоняется, голоса за книгу не должны разойтись по двум "
            "кандидатам. Число кандидатов в клубе ограничено: когда список полон, "
            "новую книгу можно предложить только после закрытия голосования.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Успешный ответ с данными номинации"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Номинировать книги могут только участники клуба"},
        404: {"description": "Книжный клуб или книга с таким id не найдены"},
        409: {"description": "Эта книга уже номинирована в клубе или список кандидатов полон"},
        503: {"description": "Google Books временно недоступен"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def nominate_book(
        club_id: PathId,
        model: CreateNominationRequest,
        user: Principal = Depends(get_current_user),
        service: NominationService = Depends(get_nomination_service)
) -> ResponseModel[NominationResponse]:
    return await service.nominate(user, club_id, model)


@router.get(
    "/{club_id}/nominations",
    response_model=ResponseModel[list[NominationResponse]],
    summary="Номинации клуба с числом голосов",
    description=(
            "Книги-кандидаты на следующий заход, в порядке номинирования. Поле "
            "`voted` отмечает номинацию, за которую отдан голос текущего "
            "пользователя.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Номинации клуба"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Книжный клуб с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_nominations(
        club_id: PathId,
        user: Principal = Depends(get_current_user),
        service: NominationService = Depends(get_nomination_service)
) -> ResponseModel[list[NominationResponse]]:
    return await service.get_nominations(user, club_id)


@router.post(
    "/{club_id}/nominations/close",
    response_model=ResponseModel[ReadingResponse],
    summary="Закрыть голосование и завести заход с книгой-победителем",
    description=(
            "Победитель - номинация с наибольшим числом голосов, при равенстве - "
            "номинированная раньше. Из неё заводится заход клуба: сроки и этапы "
            "приходят в теле запроса, как при создании захода вручную. Номинации "
            "и голоса после закрытия очищаются - следующее голосование начинается "
            "с чистого листа.\n\n"
            "Доступно только владельцу клуба.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    status_code=201,
    responses={
        201: {"description": "Заход, созданный из книги-победителя"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Пользователь не является владельцем книжного клуба"},
        404: {"description": "Книжный клуб с таким id не найден"},
        409: {"description": "В клубе нет номинаций или уже есть текущий заход"},
        422: {"description": "Ошибка валидации сроков или этапов"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def close_voting(
        club_id: PathId,
        model: ReadingScheduleRequest,
        user: Principal = Depends(get_current_user),
        service: NominationService = Depends(get_nomination_service)
) -> ResponseModel[ReadingResponse]:
    return await service.close_voting(user, club_id, model)


@nominations_router.post(
    "/{nomination_id}/vote",
    response_model=ResponseModel[NominationResponse],
    summary="Проголосовать за номинацию",
    description=(
            "У участника один голос на клуб: голос за другую номинацию "
            "переставляет его, повторный за ту же - ничего не меняет.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Номинация с обновлённым числом голосов"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Голосовать могут только участники клуба"},
        404: {"description": "Номинация с таким id не найдена"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def vote(
        nomination_id: PathId,
        user: Principal = Depends(get_current_user),
        service: NominationService = Depends(get_nomination_service)
) -> ResponseModel[NominationResponse]:
    return await service.vote(user, nomination_id)


@nominations_router.delete(
    "/{nomination_id}/vote",
    response_model=ResponseModel[NominationResponse],
    summary="Снять свой голос с номинации",
    description=(
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Номинация с обновлённым числом голосов"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Номинация с таким id не найдена"},
        409: {"description": "Голос за эту номинацию не отдавался"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def unvote(
        nomination_id: PathId,
        user: Principal = Depends(get_current_user),
        service: NominationService = Depends(get_nomination_service)
) -> ResponseModel[NominationResponse]:
    return await service.unvote(user, nomination_id)


@readings_router.put(
    "/{reading_id}/progress",
    response_model=ResponseModel[ReadingProgressResponse],
    summary="Отметить свой прогресс в заходе",
    description=(
            "Заменяет прогресс целиком: передайте `stage_id` (закрытый этап) и/или "
            "`page` (номер страницы). Если прислана только страница, закрытым "
            "считается последний этап, чей `end_page` уже прочитан.\n\n"
            "Доступно участникам клуба, пока заход не закрыт.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Обновлённый прогресс участника"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Отмечать прогресс могут только участники клуба"},
        404: {"description": "Заход или этап с таким id не найден"},
        409: {"description": "Заход уже закрыт"},
        422: {"description": "Не передан ни этап, ни страница"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def set_reading_progress(
        reading_id: PathId,
        model: UpdateReadingProgressRequest,
        user: Principal = Depends(get_current_user),
        service: ReadingService = Depends(get_reading_service)
) -> ResponseModel[ReadingProgressResponse]:
    return await service.set_progress(user, reading_id, model)


@readings_router.get(
    "/{reading_id}/progress",
    response_model=ResponseModel[Page[ReadingProgressResponse]],
    summary="Прогресс участников захода (постранично, свежие отметки сверху)",
    description=(
            "Отметки участников: закрытый этап, страница и признак `on_track` - "
            "успевает ли участник к сроку текущего этапа. Участники, не отметившие "
            "ничего, в выдаче не появляются.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Страница прогресса участников"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        404: {"description": "Заход с таким id не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def get_reading_progress(
        reading_id: PathId,
        limit: int = Query(20, ge=1, le=100),
        offset: PageOffset = 0,
        _: Principal = Depends(get_current_user),
        service: ReadingService = Depends(get_reading_service)
) -> ResponseModel[Page[ReadingProgressResponse]]:
    return await service.get_progress(reading_id, limit=limit, offset=offset)


@readings_router.post(
    "/{reading_id}/finish",
    response_model=ResponseModel[ReadingResponse],
    summary="Закрыть заход",
    description=(
            "Переводит заход в архив: клуб может завести следующий, а прогресс "
            "закрытого захода больше не меняется.\n\n"
            "Доступно только владельцу клуба.\n\n"
            "**Требуется авторизация** с заголовком:\n"
            "`X-Session-Id: <session_id>`\n\n"
    ),
    responses={
        200: {"description": "Закрытый заход"},
        401: {"description": "Ошибка авторизации (неверный токен)"},
        403: {"description": "Пользователь не является владельцем книжного клуба"},
        404: {"description": "Заход с таким id не найден"},
        409: {"description": "Заход уже закрыт"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def finish_reading(
        reading_id: PathId,
        user: Principal = Depends(get_current_user),
        service: ReadingService = Depends(get_reading_service)
) -> ResponseModel[ReadingResponse]:
    return await service.finish_reading(user, reading_id)
