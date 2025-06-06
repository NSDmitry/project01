from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY

from app.db.database import Base
from app.db.models.db_base_model import DBBaseModel


class DBBookClub(Base, DBBaseModel):
    __tablename__ = "book_clubs"

    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    owner_id = Column(Integer, nullable=False)
    members_ids = Column(ARRAY(Integer), nullable=False, default=[])