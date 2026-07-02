from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.db.models.db_base_model import DBBaseModel


class DBComment(Base, DBBaseModel):
    __tablename__ = "comments"

    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)

    author = relationship("DBUser", lazy="selectin")
