from sqlalchemy import Column, Boolean, String, BigInteger

from app.db.database import Base
from app.db.models.db_base_model import DBBaseModel


class DBUser(Base, DBBaseModel):
    __tablename__ = "users"

    name = Column(String, nullable=False)
    phone_number = Column(BigInteger, unique=True, nullable=True)
    password = Column(String, nullable=False)
    access_token = Column(String, unique=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    is_telegram_user = Column(Boolean, default=False)