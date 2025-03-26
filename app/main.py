from fastapi import FastAPI
from app.db.database import engine, Base
from app.api.routers import SSO, Users, BookClub

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(SSO.router)
app.include_router(Users.router)
app.include_router(BookClub.router)