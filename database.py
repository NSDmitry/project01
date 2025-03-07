import os

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:123123@localhost:5432/database")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=True)
Base = declarative_base()

db_session = SessionLocal()

Base.metadata.create_all(bind=engine)

def get_db():
    return db_session

def close_db():
    db_session.close()