from sqlalchemy import Column, BigInteger, String, ForeignKey, select, func
from sqlalchemy.orm import column_property

from app.core.database import Base
from app.core.db_base_model import DBLBase


class ClubMember(Base):
    __tablename__ = "club_members"

    club_id = Column(BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True)
    # id пользователя из iam - без FK, домены связаны только идентификатором
    user_id = Column(BigInteger, primary_key=True)


class BookClubGenre(Base):
    __tablename__ = "book_club_genres"

    club_id = Column(BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True)
    # id жанра из genres - без FK, домены связаны только идентификатором
    genre_id = Column(BigInteger, primary_key=True)


class BookClub(Base, DBLBase):
    __tablename__ = "book_clubs"

    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    # id пользователя из iam - без FK, обнуляется кодом при удалении владельца
    owner_id = Column(BigInteger, nullable=True)


# Счётчик считается коррелированным подзапросом прямо в SELECT клуба - один
# запрос на клуб, без загрузки строк участников и без N+1 на списках.
# threads_count здесь больше нет - треды в другом домене, счётчик
# подтягивает BookClubService батчем из ThreadRepository.
BookClub.members_count = column_property(
    select(func.count(ClubMember.user_id))
    .where(ClubMember.club_id == BookClub.id)
    .scalar_subquery()
)
