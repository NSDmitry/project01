from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.db_base_model import DBLBase


class Thread(Base, DBLBase):
    __tablename__ = "threads"

    club_id = Column(Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)

    author = relationship("User", lazy="selectin")
    club = relationship("BookClub", lazy="selectin")


class Comment(Base, DBLBase):
    __tablename__ = "comments"

    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)

    author = relationship("User", lazy="selectin")
