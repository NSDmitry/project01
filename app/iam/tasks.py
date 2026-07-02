"""Удаляет неактивные сессии (last_used старше SESSION_MAX_IDLE).

Запускается по расписанию (cron / k8s CronJob), вне процесса приложения:

    python -m app.iam.tasks
"""
import asyncio

from app.core.database import AsyncSessionLocal
from app.iam.repository import UserSessionRepository
from app.iam.service import UserSessionService


async def main() -> int:
    async with AsyncSessionLocal() as db:
        service = UserSessionService(UserSessionRepository(db))
        deleted = await service.cleanup_idle_sessions()
        await db.commit()
        print(f"Deleted {deleted} idle user session(s)")
        return deleted


if __name__ == "__main__":
    asyncio.run(main())
