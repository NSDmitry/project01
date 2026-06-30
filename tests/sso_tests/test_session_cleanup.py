from datetime import timedelta

from app.api.services.user_session_service import UserSessionService
from app.db.models.db_user_session import DBUserSession
from app.db.repositories.user_session_repository import UserSessionRepository
from tests.support.flows import AuthFlow


class TestIdleSessionCleanup:
    def _service(self, db) -> UserSessionService:
        return UserSessionService(UserSessionRepository(db))

    def _session(self, db, user_id: int) -> DBUserSession:
        db.expire_all()
        return db.query(DBUserSession).filter(DBUserSession.user_id == user_id).first()

    def test_cleanup_removes_idle_sessions(self, api, db):
        idle = AuthFlow.register(api)
        session = self._session(db, idle.user_id)
        session.last_used = session.last_used - timedelta(days=31)
        db.commit()

        deleted = self._service(db).cleanup_idle_sessions()

        assert deleted == 1
        assert self._session(db, idle.user_id) is None

    def test_cleanup_keeps_active_sessions(self, api, db):
        active = AuthFlow.register(api)

        deleted = self._service(db).cleanup_idle_sessions()

        assert deleted == 0
        assert self._session(db, active.user_id) is not None

    def test_cleanup_removes_sessions_without_last_used(self, api, db):
        legacy = AuthFlow.register(api)
        session = self._session(db, legacy.user_id)
        session.last_used = None
        db.commit()

        deleted = self._service(db).cleanup_idle_sessions()

        assert deleted == 1
        assert self._session(db, legacy.user_id) is None
