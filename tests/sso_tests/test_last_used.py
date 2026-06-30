from datetime import timedelta

from app.db.models.db_user_session import DBUserSession
from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow


class TestSessionLastUsed:
    def _session(self, db, user_id: int) -> DBUserSession:
        db.expire_all()
        return db.query(DBUserSession).filter(DBUserSession.user_id == user_id).first()

    def _shift_last_used(self, db, user_id: int, delta: timedelta):
        session = self._session(db, user_id)
        session.last_used = session.last_used - delta
        db.commit()

    def test_last_used_is_set_on_session_creation(self, api, db):
        auth = AuthFlow.register(api)
        assert self._session(db, auth.user_id).last_used is not None

    def test_last_used_not_rewritten_within_throttle_window(self, api, db):
        auth = AuthFlow.register(api)

        api.public_user(auth.user_id, headers=auth.headers)
        first = self._session(db, auth.user_id).last_used

        api.public_user(auth.user_id, headers=auth.headers)
        second = self._session(db, auth.user_id).last_used

        assert second == first

    def test_last_used_updated_after_throttle_window(self, api, db):
        auth = AuthFlow.register(api)

        # Сдвигаем last_used за пределы окна троттлинга, чтобы не ждать реальные 5 минут
        self._shift_last_used(db, auth.user_id, timedelta(minutes=6))
        stale = self._session(db, auth.user_id).last_used

        api.public_user(auth.user_id, headers=auth.headers)

        assert self._session(db, auth.user_id).last_used > stale

    def test_request_allowed_within_max_idle(self, api, db):
        auth = AuthFlow.register(api)
        self._shift_last_used(db, auth.user_id, timedelta(days=29))

        response = api.public_user(auth.user_id, headers=auth.headers)

        assert_status_code(response, 200)

    def test_request_rejected_when_idle_over_max(self, api, db):
        auth = AuthFlow.register(api)
        self._shift_last_used(db, auth.user_id, timedelta(days=31))

        response = api.public_user(auth.user_id, headers=auth.headers)

        assert_status_code(response, 401)
        assert "session_expired" in response.json()["errors"]
