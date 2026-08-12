from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from service.database import Base


class Delivery(Base):
    """Очередь доставки. Строка появляется из батча монолита (relay), дубль повторного
    батча гасится UNIQUE event_id. Доставляет воркер service.worker."""
    __tablename__ = "deliveries"
    __table_args__ = (
        # Скан воркера: только недоставленные строки.
        Index("ix_deliveries_pending", "id", postgresql_where=text("processed_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # id строки outbox монолита - ключ идемпотентности приёма.
    event_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    # Снапшот привязки получателя на момент relay - сервис в БД монолита не ходит.
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # NULL - ждёт доставки. Ставится и при доставке, и когда доставлять нечего.
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
