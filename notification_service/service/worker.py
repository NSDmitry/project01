"""Доставка уведомлений из таблицы deliveries.

Запускается по расписанию, вне процесса API:

    python -m service.worker

Прогон обрабатывает одну пачку; хвост дольёт следующий запуск по расписанию.
"""
import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from service import channels
from service.database import AsyncSessionLocal
from service.models import Delivery

# После этого числа неудачных попыток строка выпадает из выборки воркера:
# канал стабильно отвечает ошибкой (например, получатель заблокировал бота).
MAX_ATTEMPTS = 5

# Все каналы доставки. Новый провайдер (email/sms) - функция в channels.py
# и строка здесь.
CHANNELS = [channels.send_telegram]


async def deliver_pending(db: AsyncSession, limit: int = 500) -> int:
    """Обрабатывает пачку недоставленных строк, возвращает число доставленных.

    FOR UPDATE SKIP LOCKED: два одновременных прогона воркера не отправят
    одну строку дважды.
    """
    result = await db.execute(
        select(Delivery)
        .where(Delivery.processed_at.is_(None), Delivery.attempts < MAX_ATTEMPTS)
        .order_by(Delivery.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    deliveries = result.scalars().all()

    delivered = 0
    for delivery in deliveries:
        outcomes = [await channel(delivery.chat_id, delivery.text) for channel in CHANNELS]
        if True in outcomes:
            delivery.processed_at = func.now()
            delivered += 1
        elif all(outcome is None for outcome in outcomes):
            # Ни один канал не применим - ждать нечего, закрываем строку.
            delivery.processed_at = func.now()
        else:
            delivery.attempts += 1

    return delivered


async def main() -> None:
    async with AsyncSessionLocal() as db:
        delivered = await deliver_pending(db)
        await db.commit()
        print(f"Delivered {delivered} notification(s)")


if __name__ == "__main__":
    asyncio.run(main())
