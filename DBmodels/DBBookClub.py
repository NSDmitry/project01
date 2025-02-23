from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class DBBookClub(Base):
    __tablename__ = "book_clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    owner_id = Column(Integer, nullable=False)
    members = relationship("DBUser", secondary="user_bookclub", back_populates="book_clubs")