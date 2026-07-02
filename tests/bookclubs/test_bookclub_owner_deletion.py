from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow


class TestBookclubOwnerDeletion:
    def test_deleting_owner_keeps_club_with_null_owner(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        reader = AuthFlow.register(api)

        # Эндпоинта удаления пользователя нет - удаляем строку напрямую, чтобы
        # проверить FK ON DELETE SET NULL на уровне БД.
        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": owner.user_id})
        db.commit()

        response = api.bookclub(club_id, headers=reader.headers)
        assert_status_code(response, 200)
        assert response.json()["data"]["owner"] is None
