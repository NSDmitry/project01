import uuid

from sqlalchemy import Column, UUID, Integer, String, DateTime

from app.db.database import Base
from app.db.models import DBBaseModel


class DBUserSession(Base, DBBaseModel):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False)
    sid_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
