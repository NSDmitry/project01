import hmac
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from redis import asyncio as redis_asyncio

# Импорт ради side-effect: регистрация доменных подписчиков на события.
# Через from-import, иначе имя `app` связывается с пакетом и конфликтует с `app = FastAPI()`.
from app.bookclubs import events as _bookclubs_events  # noqa: F401
from app.threads import events as _threads_events  # noqa: F401
from app.bookclubs.router import router as bookclubs_router, nominations_router, readings_router
from app.books.router import router as books_router
from app.core import events, media
from app.core.errors.APIException import APIException
from app.core.models.response_model import ResponseModel
from app.genres.router import router as genres_router
from app.iam.router import auth_router, users_router
from app.settings import settings
from app.threads.router import threads_router, comments_router


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    redis_conn = redis_asyncio.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_conn)
    await events.startup()
    try:
        yield
    finally:
        await events.shutdown()
        await FastAPILimiter.close()


app = FastAPI(
    default_response_class=UTF8JSONResponse,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

if settings.docs_enabled:
    openapi_url = app.openapi_url or "/openapi.json"
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != openapi_url]

    @app.api_route(openapi_url, methods=["GET", "HEAD"], include_in_schema=False)
    def openapi() -> dict[str, Any]:
        return app.openapi()


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(bookclubs_router)
app.include_router(readings_router)
app.include_router(nominations_router)
app.include_router(threads_router)
app.include_router(comments_router)
app.include_router(genres_router)
app.include_router(books_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_urls,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app)


def verify_metrics_token(authorization: str = Header(default="")) -> None:
    if not settings.metrics_token:
        # Токен не задан - метрики недоступны наружу.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not hmac.compare_digest(authorization, f"Bearer {settings.metrics_token}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@app.get("/metrics", include_in_schema=False, dependencies=[Depends(verify_metrics_token)])
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/media/{key:path}", include_in_schema=False)
async def get_media(key: str) -> Response:
    """Раздача загруженных картинок - бакет приватный, ссылок наружу не выдаём."""
    data = await media.read_image(key)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Ключ содержит uuid, файл по нему не меняется никогда - можно кэшировать
    # навсегда, повторных запросов за картинкой не будет.
    return Response(
        data,
        media_type=media.CONTENT_TYPE,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.exception_handler(APIException)
def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    return exc.as_response()


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for e in exc.errors():
        msg = e["msg"].removeprefix("Value error, ")
        # loc[0] - источник (body/query/path), дальше - путь до поля.
        field = ".".join(str(part) for part in e["loc"][1:])
        errors.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResponseModel.fail(message="Невозможно обработать запрос", errors=errors).model_dump(),
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Обработчик регистрируется в ServerErrorMiddleware, который сам traceback
    # не логирует - без exception() ошибка пропадёт из логов.
    logging.getLogger("app").exception("Unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ResponseModel.fail(message="Внутренняя ошибка сервера").model_dump(),
    )
