import pytest

from app.api.services.user_session_service import UserSessionService
from app.db.models.db_user import DBUser
from tests.support.factories import AuthFactory


class TestRegisterAtomicity:
    def test_register_rolls_back_user_when_session_creation_fails(self, api, db, monkeypatch):
        # Регрессия на Unit of Work: create_user и create_user_session - одна
        # транзакция. Если создание сессии падает, юзер не должен остаться в БД.
        async def boom(self, user_id):
            raise RuntimeError("session creation failed")

        monkeypatch.setattr(UserSessionService, "create_user_session", boom)

        with pytest.raises(RuntimeError):
            api.register(AuthFactory.register_payload())

        db.expire_all()
        assert db.query(DBUser).count() == 0
