from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors.APIException import APIException
from app.core.models.response_model import ResponseModel
from app.api.routers import auth, users, book_club, discussions
from fastapi.middleware.cors import CORSMiddleware
from app.settings import settings

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(book_club.router)
app.include_router(discussions.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_urls,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from prometheus_fastapi_instrumentator import Instrumentator
ins = Instrumentator().instrument(app)
ins.expose(
    app,
    include_in_schema=False,
    endpoint="/metrics",
)

@app.exception_handler(APIException)
def api_exception_handler(request: Request, exc: APIException):
    return exc.as_response()


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [e["msg"].removeprefix("Value error, ") for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResponseModel.fail(message="Невозможно обработать запрос", errors=errors).model_dump(),
    )