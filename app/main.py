from fastapi import FastAPI, Request

from app.core.errors.APIExeption import APIException
from app.db.database import engine, Base
from app.api.routers import sso, users, book_club, discussions
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(sso.router)
app.include_router(users.router)
app.include_router(book_club.router)
app.include_router(discussions.router)

origins = [
    "https://nsdmitrij.ru",
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(APIException)
def api_exception_handler(request: Request, exc: APIException):
    return exc.as_response()