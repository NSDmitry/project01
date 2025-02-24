from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base

class DBBookClub(Base):
    __tablename__ = "book_clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("DBUser", back_populates="owned_clubs")
    members = relationship("DBUser", secondary="user_bookclub", back_populates="book_clubs")