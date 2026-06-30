"""Удаляет неактивные сессии (last_used старше SESSION_MAX_IDLE).

Запускается по расписанию (cron / k8s CronJob), вне процесса приложения:

    python -m app.tasks.cleanup_sessions
"""
import asyncio

from app.api.services.user_session_service import UserSessionService
from app.db.database import AsyncSessionLocal
from app.db.repositories.user_session_repository import UserSessionRepository


async def main() -> int:
    async with AsyncSessionLocal() as db:
        service = UserSessionService(UserSessionRepository(db))
        deleted = await service.cleanup_idle_sessions()
        await db.commit()
        print(f"Deleted {deleted} idle user session(s)")
        return deleted


if __name__ == "__main__":
    asyncio.run(main())
