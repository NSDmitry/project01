from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestThreadAuthorDeletion:
    def test_deleting_author_keeps_thread_with_null_author(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        author = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=author.headers), 200)
        api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, title="Тред автора"), headers=author.headers
        )

        # Эндпоинта удаления пользователя нет - удаляем строку напрямую, чтобы
        # проверить FK ON DELETE SET NULL на уровне БД.
        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": author.user_id})
        db.commit()

        page = api.threads(club_id, headers=owner.headers)
        assert_status_code(page, 200)

        items = page.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Тред автора"
        assert items[0]["author"] is None
