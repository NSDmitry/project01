import hashlib
from datetime import datetime, timedelta, timezone
import secrets

from app.core.errors.errors import Unauthorized
from app.db.models.db_user_session import DBUserSession
from app.db.repositories.user_session_repository import UserSessionRepository

LAST_USED_THRESHOLD = timedelta(minutes=5)
SESSION_MAX_IDLE = timedelta(days=30)

class UserSessionService:
    user_session_repository: UserSessionRepository

    def __init__(self, user_session_repository: UserSessionRepository) -> None:
        self.user_session_repository = user_session_repository

    def create_user_session(self, user_id: int) -> str:
        now = self._utcnow()

        sid = self._generate_sid()
        sid_hash = self._sid_hash(sid)

        _ = self.user_session_repository.create_user_session(
            user_id=user_id,
            sid_hash=sid_hash,
            last_used=now
        )

        return sid

    def get_user_session(self, sid: str) -> DBUserSession:
        sid_hash = self._sid_hash(sid)
        session = self.user_session_repository.get_user_session(sid_hash)

        if not session:
            return None

        now = self._utcnow()

        if session.last_used is None or session.last_used < now - SESSION_MAX_IDLE:
            raise Unauthorized(
                message="Сессия истекла из-за длительной неактивности",
                errors=["session_expired"],
            )

        if session.last_used < now - LAST_USED_THRESHOLD:
            self.user_session_repository.update_last_used(session, now)

        return session

    def logout_user_session(self, sid: str):
        sid_hash = self._sid_hash(sid)
        self.user_session_repository.delete_user_session(sid_hash)

    def logout_all_user_sessions(self, user_id: int):
        self.user_session_repository.delete_all_user_sessions(user_id)

    def cleanup_idle_sessions(self) -> int:
        cutoff = self._utcnow() - SESSION_MAX_IDLE
        return self.user_session_repository.delete_idle_sessions(cutoff)

    @staticmethod
    def _generate_sid() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _sid_hash(sid: str) -> str:
        return hashlib.sha256(sid.encode("utf-8")).hexdigest()

    @staticmethod
    def _utcnow():
        return datetime.now(timezone.utc)
