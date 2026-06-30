from sqlalchemy import Column, Integer, String, ForeignKey, select, func
from sqlalchemy.orm import relationship, column_property

from app.db.database import Base
from app.db.models.db_base_model import DBBaseModel
from app.db.models.db_club_member import DBClubMember
from app.db.models.db_discussion import DBDiscussion


class DBBookClub(Base, DBBaseModel):
    __tablename__ = "book_clubs"

    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("DBUser", lazy="selectin")


# Счётчики считаются коррелированным подзапросом прямо в SELECT клуба - один
# запрос на клуб, без загрузки строк участников/обсуждений и без N+1 на списках.
DBBookClub.members_count = column_property(
    select(func.count(DBClubMember.user_id))
    .where(DBClubMember.club_id == DBBookClub.id)
    .scalar_subquery()
)

DBBookClub.discussions_count = column_property(
    select(func.count(DBDiscussion.id))
    .where(DBDiscussion.club_id == DBBookClub.id)
    .scalar_subquery()
)
