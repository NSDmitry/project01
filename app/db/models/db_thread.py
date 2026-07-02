from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.db.models.db_base_model import DBBaseModel


class DBThread(Base, DBBaseModel):
    __tablename__ = "threads"

    club_id = Column(Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)

    author = relationship("DBUser", lazy="selectin")
    club = relationship("DBBookClub", lazy="selectin")
