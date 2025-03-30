from sqlalchemy import Column, Integer, String, Text

from app.db.database import Base
from app.db.models import DBBaseModel


class DBDiscussion(DBBaseModel, Base):
    __tablename__ = "discussions"

    club_id = Column(Integer, nullable=False)
    author_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)