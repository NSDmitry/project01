import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from app.settings import settings

load_dotenv()

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=True)
Base = declarative_base()

db_session = SessionLocal()

Base.metadata.create_all(bind=engine)

def get_db():
    return db_session

def close_db():
    db_session.close()