from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import ARRAY

from app.db.database import Base

class DBBookClub(Base):
    __tablename__ = "book_clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    owner_id = Column(Integer, nullable=False)
    members_ids = Column(ARRAY(Integer), nullable=False, default=[])