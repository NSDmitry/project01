"""Relay уведомлений: outbox -> notification-service.

Запускается по расписанию (cron / k8s CronJob), вне процесса приложения:

    python -m app.notifications.tasks

Прогон: генерирует напоминания о завтрашних дедлайнах (идемпотентно) и передаёт
накопившиеся строки outbox батчем в notification-service. Доставку по каналам
выполняет сам сервис (notification_service/), монолит каналов больше не знает.
"""
import asyncio
import logging

import httpx
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.iam.repository import UserRepository
from app.notifications.repository import NotificationRepository
from app.settings import settings

logger = logging.getLogger("app.notifications")


async def _post_batch(batch: list[dict[str, int | str]]) -> bool:
    """POST батча в сервис; True = сервис принял (202)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.notification_service_url}/v1/notifications:batch",
                json=batch,
                headers={"X-Internal-Token": settings.internal_token},
            )
    except httpx.HTTPError as error:
        logger.warning("notification-service недоступен: %s", error)
        return False

    if response.status_code != 202:
        logger.warning("notification-service ответил %s: %s", response.status_code, response.text)
        return False

    return True


async def relay_pending(db: AsyncSession) -> int:
    """Передаёт пачку строк outbox в сервис, возвращает число переданных.

    Строки помечаются обработанными только после 202: недоступность сервиса
    оставляет их в outbox без потерь, дубль повторной передачи гасится
    UNIQUE event_id на стороне сервиса.

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

    batch: list[dict[str, int | str]] = []
    sent_rows = []
    for notification in notifications:
        user = users.get(notification.user_id)
        # Пользователь удалён (гонка с каскадом), тип отключён или нет ни одной
        # привязки канала - передавать нечего, закрываем строку.
        if (
            user is None
            or notification.type in user.disabled_notifications
            or user.telegram_id is None
        ):
            notification.processed_at = func.now()
            continue

        batch.append(
            {
                "event_id": notification.id,
                # Снапшот привязки на момент relay: сервис в БД монолита не ходит.
                "telegram_chat_id": user.telegram_id,
                "text": notification.text,
            }
        )
        sent_rows.append(notification)

    if not batch or not await _post_batch(batch):
        return 0

    for notification in sent_rows:
        notification.processed_at = func.now()

    return len(sent_rows)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await NotificationRepository(db).create_deadline_reminders()
        await db.commit()

        relayed = await relay_pending(db)
        await db.commit()
        print(f"Relayed {relayed} notification(s)")


if __name__ == "__main__":
    asyncio.run(main())
