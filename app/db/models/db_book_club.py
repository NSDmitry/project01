from sqlalchemy import Column, Integer, String, ForeignKey, select, func
from sqlalchemy.orm import relationship, column_property

from app.db.database import Base
from app.db.models.db_base_model import DBBaseModel
from app.db.models.db_club_member import DBClubMember
from app.db.models.db_thread import DBThread


class DBBookClub(Base, DBBaseModel):
    __tablename__ = "book_clubs"

    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    owner = relationship("DBUser", lazy="selectin")


# Счётчики считаются коррелированным подзапросом прямо в SELECT клуба - один
# запрос на клуб, без загрузки строк участников/тредов и без N+1 на списках.
DBBookClub.members_count = column_property(
    select(func.count(DBClubMember.user_id))
    .where(DBClubMember.club_id == DBBookClub.id)
    .scalar_subquery()
)

DBBookClub.threads_count = column_property(
    select(func.count(DBThread.id))
    .where(DBThread.club_id == DBBookClub.id)
    .scalar_subquery()
)
