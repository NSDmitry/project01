from sqlalchemy import BigInteger, String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_base_model import DBLBase


class ClubMember(Base):
    __tablename__ = "club_members"
    __table_args__ = (
        # PK (club_id, user_id) обслуживает выборку по club_id (префикс), но не
        # по одному user_id: «мои клубы» и удаление пользователя.
        Index("ix_club_members_user_id", "user_id"),
    )

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True
    )
    # id пользователя из iam - без FK, домены связаны только идентификатором
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class BookClubGenre(Base):
    __tablename__ = "book_club_genres"

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True
    )
    # id жанра из genres - без FK, домены связаны только идентификатором
    genre_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class BookClub(Base, DBLBase):
    __tablename__ = "book_clubs"
    __table_args__ = (
        # Фильтр «мои клубы» по владению и обнуление владельца при удалении пользователя.
        Index("ix_book_clubs_owner_id", "owner_id"),
    )

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    # id пользователя из iam - без FK, обнуляется кодом при удалении владельца
    owner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Денормализованный счётчик тредов клуба. Треды - в другом домене (без FK),
    # поэтому клуб не считает их подзапросом, а ведёт столбец по событиям
    # THREAD_CREATED/THREAD_DELETED (см. events.py).
    threads_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
