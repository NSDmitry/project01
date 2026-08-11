"""Доставка уведомлений из таблицы notifications.

Запускается по расписанию (cron / k8s CronJob), вне процесса приложения:

    python -m app.notifications.tasks

Прогон: генерирует напоминания о завтрашних дедлайнах (идемпотентно) и
доставляет накопившиеся уведомления по каналам из CHANNELS.
"""
import asyncio

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.iam.repository import UserRepository
from app.notifications import sender
from app.notifications.repository import NotificationRepository

# Все каналы доставки. Новый провайдер (email/sms) - функция в sender.py
# и строка здесь.
CHANNELS = [sender.send_telegram]


async def deliver_pending(db: AsyncSession) -> int:
    """Обрабатывает пачку недоставленных уведомлений, возвращает число доставленных.

    # ponytail: одна пачка за прогон; хвост дольёт следующий запуск по расписанию.
    """
    notifications = await NotificationRepository(db).pick_pending()
    if not notifications:
        return 0

    users = {
        user.id: user
        for user in await UserRepository(db).get_users_by_ids(
            list({notification.user_id for notification in notifications})
        )
    }

    delivered = 0
    for notification in notifications:
        user = users.get(notification.user_id)
        # Пользователь удалён (гонка с каскадом) или тип отключён - доставлять нечего.
        if user is None or notification.type in user.disabled_notifications:
            notification.processed_at = func.now()
            continue

        results = [await channel(user, notification.text) for channel in CHANNELS]
        if True in results:
            notification.processed_at = func.now()
            delivered += 1
        elif all(result is None for result in results):
            # Ни одного привязанного канала - ждать нечего, закрываем строку.
            notification.processed_at = func.now()
        else:
            notification.attempts += 1

    return delivered


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await NotificationRepository(db).create_deadline_reminders()
        await db.commit()

        delivered = await deliver_pending(db)
        await db.commit()
        print(f"Delivered {delivered} notification(s)")


if __name__ == "__main__":
    asyncio.run(main())
