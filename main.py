from fastapi import FastAPI
from database import engine, Base
from routers import SSO, Users, BookClub

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(SSO.router)
app.include_router(Users.router)
app.include_router(BookClub.router)