"""Удаляет неактивные сессии (last_used старше SESSION_MAX_IDLE).

Запускается по расписанию (cron / k8s CronJob), вне процесса приложения:

    python -m app.tasks.cleanup_sessions
"""
from app.api.services.user_session_service import UserSessionService
from app.db.database import SessionLocal
from app.db.repositories.user_session_repository import UserSessionRepository


def main() -> int:
    db = SessionLocal()
    try:
        service = UserSessionService(UserSessionRepository(db))
        deleted = service.cleanup_idle_sessions()
        print(f"Deleted {deleted} idle user session(s)")
        return deleted
    finally:
        db.close()


if __name__ == "__main__":
    main()
