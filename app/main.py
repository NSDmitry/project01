from fastapi import FastAPI, Request

from app.core.errors.APIExeption import APIException
from app.db.database import engine, Base
from app.api.routers import sso, users, book_club, discussions

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(sso.router)
app.include_router(users.router)
app.include_router(book_club.router)
app.include_router(discussions.router)

@app.exception_handler(APIException)
def api_exception_handler(request: Request, exc: APIException):
    return exc.as_response()