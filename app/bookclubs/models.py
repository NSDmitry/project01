from sqlalchemy import Column, BigInteger, Integer, Boolean, String, ForeignKey, select, func
from sqlalchemy.orm import relationship, column_property

from app.core.database import Base
from app.core.db_base_model import DBLBase
from app.discussions.models import Thread


class ClubMember(Base):
    __tablename__ = "club_members"

    club_id = Column(BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class Genre(Base):
    __tablename__ = "genres"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default=func.true())


class BookClubGenre(Base):
    __tablename__ = "book_club_genres"

    club_id = Column(BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True)
    genre_id = Column(BigInteger, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)


class BookClub(Base, DBLBase):
    __tablename__ = "book_clubs"

    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    owner_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    owner = relationship("User", lazy="selectin")
    genres = relationship(
        "Genre",
        secondary="book_club_genres",
        lazy="selectin",
        order_by="Genre.sort_order",
    )


# Счётчики считаются коррелированным подзапросом прямо в SELECT клуба - один
# запрос на клуб, без загрузки строк участников/тредов и без N+1 на списках.
BookClub.members_count = column_property(
    select(func.count(ClubMember.user_id))
    .where(ClubMember.club_id == BookClub.id)
    .scalar_subquery()
)

BookClub.threads_count = column_property(
    select(func.count(Thread.id))
    .where(Thread.club_id == BookClub.id)
    .scalar_subquery()
)
