from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_base_model import DBLBase


class Book(Base, DBLBase):
    __tablename__ = "books"

    # NULL - книга создана пользователем вручную, без Google Books.
    google_volume_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    genres: Mapped[str | None] = mapped_column(String, nullable=True)
    published_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
