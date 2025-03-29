from typing import Dict

from sqlalchemy import Column, Integer, func, DateTime
from typing_extensions import Any


class DBBaseModel:
    """Base model class for all database models."""
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for serialization."""
        result = {}
        for column in self.__table__.columns:
            result[column.name] = getattr(self, column.name)
        return result