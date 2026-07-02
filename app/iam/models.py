import uuid

from sqlalchemy import Column, String, BigInteger, UUID, Integer, DateTime

from app.core.database import Base
from app.core.db_base_model import DBLBase


class User(Base, DBLBase):
    __tablename__ = "users"

    name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    password = Column(String, nullable=True)


class UserSession(Base, DBLBase):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False)
    sid_hash = Column(String(64), nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
