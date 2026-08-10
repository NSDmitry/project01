import uuid
from datetime import datetime

from sqlalchemy import String, BigInteger, UUID, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_base_model import DBLBase


class User(Base, DBLBase):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    password: Mapped[str | None] = mapped_column(String, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class UserSession(Base, DBLBase):
    __tablename__ = "user_sessions"
    __table_args__ = (
        # Поиск сессии по sid_hash - на каждом авторизованном запросе.
        Index("ix_user_sessions_sid_hash", "sid_hash", unique=True),
        # Сессии одного пользователя, свежие сначала: подрезка лимита сессий
        # и логаут со всех устройств. Порядок ASC обслуживает и ORDER BY DESC
        # (Index Scan Backward), отдельный DESC-индекс не нужен.
        Index("ix_user_sessions_user_id_last_used", "user_id", "last_used"),
    )

    # Сессии адресуются UUID, а не автоинкрементом из DBLBase - осознанное переопределение.
    id: Mapped[uuid.UUID] = mapped_column(  # type: ignore[assignment]
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sid_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
