from sqlalchemy import Column, Integer, String
from database import Base

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    rating = Column(Integer)
    author = Column(String, nullable=True)