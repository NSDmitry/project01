from sqlalchemy import Column, Integer, String, BigInteger

from database import Base

class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(BigInteger, unique=True, nullable=False)
    password = Column(String, nullable=False)
    access_token = Column(String, unique=True, nullable=False)