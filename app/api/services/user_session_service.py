import hashlib
from datetime import datetime, timedelta, timezone
import secrets

from app.db.models.db_user_session import DBUserSession
from app.db.repositories.user_session_repository import UserSessionRepository

SESSION_TTL_DAYS = 30

class UserSessionService:
    user_session_repository: UserSessionRepository

    def __init__(self, user_session_repository: UserSessionRepository) -> None:
        self.user_session_repository = user_session_repository

    def create_user_session(self, user_id: int) -> str:
        now = self._utcnow()

        sid = self._generate_sid()
        sid_hash = self._sid_hash(sid)
        expires_at = now + timedelta(days=SESSION_TTL_DAYS)

        _ = self.user_session_repository.create_user_session(
            user_id=user_id,
            sid_hash=sid_hash,
            expires_at=expires_at
        )

        return sid

    def get_user_session(self, sid: str) -> DBUserSession:
        sid_hash = self._sid_hash(sid)
        return self.user_session_repository.get_user_session(sid_hash)

    def logout_user_session(self, sid: str):
        sid_hash = self._sid_hash(sid)
        self.user_session_repository.delete_user_session(sid_hash)

    def logout_all_user_sessions(self, user_id: int):
        self.user_session_repository.delete_all_user_sessions(user_id)

    @staticmethod
    def _generate_sid() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _sid_hash(sid: str) -> str:
        return hashlib.sha256(sid.encode("utf-8")).hexdigest()

    @staticmethod
    def _utcnow():
        return datetime.now(timezone.utc)
