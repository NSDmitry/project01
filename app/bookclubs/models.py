from sqlalchemy import BigInteger, String, ForeignKey, select, func
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.core.database import Base
from app.core.db_base_model import DBLBase


class ClubMember(Base):
    __tablename__ = "club_members"

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

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    # id пользователя из iam - без FK, обнуляется кодом при удалении владельца
    owner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Денормализованный счётчик тредов клуба. Треды - в другом домене (без FK),
    # поэтому клуб не считает их подзапросом, а ведёт столбец по событиям
    # THREAD_CREATED/THREAD_DELETED (см. events.py).
    threads_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")


# Счётчик участников считается коррелированным подзапросом прямо в SELECT клуба -
# один запрос на клуб, без загрузки строк участников и без N+1 на списках.
BookClub.members_count = column_property(
    select(func.count(ClubMember.user_id))
    .where(ClubMember.club_id == BookClub.id)
    .scalar_subquery()
)
