from fastapi import FastAPI, Request

from app.core.errors.APIExeption import APIException
from app.db.database import engine, Base
from app.api.routers import sso, users, book_club, discussions
from fastapi.middleware.cors import CORSMiddleware
from app.settings import settings

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(sso.router)
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