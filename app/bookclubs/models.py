from sqlalchemy import Column, Integer, String, ForeignKey, select, func
from sqlalchemy.orm import relationship, column_property

from app.core.database import Base
from app.core.db_base_model import DBLBase
from app.discussions.models import Thread


class ClubMember(Base):
    __tablename__ = "club_members"

    club_id = Column(Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class BookClub(Base, DBLBase):
    __tablename__ = "book_clubs"

    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    owner = relationship("User", lazy="selectin")


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
