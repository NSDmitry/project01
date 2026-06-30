from sqlalchemy import Column, String

from app.db.database import Base
from app.db.models.db_base_model import DBBaseModel


class DBUser(Base, DBBaseModel):
    __tablename__ = "users"

    name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=False)