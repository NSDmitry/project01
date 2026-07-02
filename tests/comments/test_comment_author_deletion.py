from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestCommentAuthorDeletion:
    def test_deleting_author_keeps_comment_with_null_author(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        author = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=author.headers), 200)
        api.create_comment(
            thread_id, CommentFactory.create_payload(content="Комментарий автора"), headers=author.headers
        )

        # Эндпоинта удаления пользователя нет - удаляем строку напрямую, чтобы
        # проверить FK ON DELETE SET NULL на уровне БД.
        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": author.user_id})
        db.commit()

        page = api.comments(thread_id, headers=owner.headers)
        assert_status_code(page, 200)

        items = page.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["content"] == "Комментарий автора"
        assert items[0]["author"] is None

    def test_deleting_thread_cascades_comments(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        api.create_comment(thread_id, CommentFactory.create_payload(), headers=owner.headers)

        assert_status_code(api.delete_thread(thread_id, headers=owner.headers), 200)

        remaining = db.execute(
            text("SELECT count(*) FROM comments WHERE thread_id = :thread_id"),
            {"thread_id": thread_id},
        ).scalar()
        assert remaining == 0
