from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_base_model import DBLBase


class NotificationType(StrEnum):
    """Типы уведомлений. Каждый пользователь может отключить любой из них
    (users.disabled_notifications)."""
    COMMENT_IN_THREAD = "comment_in_thread"
    READING_STARTED = "reading_started"
    STAGE_DEADLINE = "stage_deadline"
    READING_DEADLINE = "reading_deadline"


class Notification(Base, DBLBase):
    """Очередь уведомлений (outbox в Postgres, брокер не нужен): строка создаётся
    в той же транзакции, что и породившее её событие, доставляет её воркер
    app.notifications.tasks вне процесса приложения."""
    __tablename__ = "notifications"
    __table_args__ = (
        # Скан воркера: только недоставленные строки, обработанные в индекс не попадают.
        Index("ix_notifications_pending", "id", postgresql_where=text("processed_at IS NULL")),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    # Готовый текст сообщения: рендерится в момент события, когда контекст
    # (название клуба, треда) уже под рукой - воркеру не нужны join-ы.
    text: Mapped[str] = mapped_column(String, nullable=False)
    # Ключ идемпотентности напоминаний, генерируемых по расписанию: повторный
    # прогон не создаёт дубликат (ON CONFLICT DO NOTHING). У событийных
    # уведомлений NULL - на NULL уникальность не срабатывает.
    dedup_key: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    # NULL - ждёт доставки. Ставится и при доставке, и когда доставлять нечего:
    # у пользователя нет ни одного канала или тип отключён.
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
