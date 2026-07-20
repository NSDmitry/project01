from sqlalchemy import Column, BigInteger, Integer, String

from app.core.database import Base


class Genre(Base):
    __tablename__ = "genres"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
