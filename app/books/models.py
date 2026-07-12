from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base
from app.core.db_base_model import DBLBase


class Book(Base, DBLBase):
    __tablename__ = "books"

    # NULL - книга создана пользователем вручную, без Google Books.
    google_volume_id = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    genres = Column(String, nullable=True)
    published_year = Column(Integer, nullable=True)
