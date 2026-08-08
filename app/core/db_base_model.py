from datetime import datetime

from sqlalchemy import BigInteger, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column


class DBLBase:
    """Base model class for all database models."""
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False
    )
