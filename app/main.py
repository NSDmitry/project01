from fastapi import FastAPI
from app.db.database import engine, Base
from app.api.routers import sso, users, book_club

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(sso.router)
app.include_router(users.router)
app.include_router(book_club.router)