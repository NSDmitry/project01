from sqlalchemy import Column, Integer, String, ARRAY, Table, ForeignKey
from sqlalchemy.orm import relationship
from DBmodels.association import user_bookclub

from database import Base

class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(Integer, unique=True, nullable=False)
    password = Column(String, nullable=False)
    access_token = Column(String, unique=True, nullable=False)
    book_clubs = relationship("DBBookClub", secondary="user_bookclub", back_populates="members")