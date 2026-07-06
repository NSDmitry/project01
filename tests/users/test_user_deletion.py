from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


def _count(db, table, column, value):
    return db.execute(
        text(f"SELECT count(*) FROM {table} WHERE {column} = :value"), {"value": value}
    ).scalar()


def _seed_content(api):
    user = AuthFlow.register(api)
    club_id = BookclubFlow.create(api, auth=user).json()["data"]["id"]
    thread_id = api.create_thread(
        ThreadFactory.create_payload(club_id=club_id), headers=user.headers
    ).json()["data"]["id"]
    comment_id = api.create_comment(
        thread_id, CommentFactory.create_payload(), headers=user.headers
    ).json()["data"]["id"]

    return user, club_id, thread_id, comment_id


class TestUserDeletion:
    def test_requires_authorization(self, api):
        assert_status_code(api.delete_current_user(headers={}), 401)

    def test_removes_user_and_sessions(self, api, db):
        user = AuthFlow.register(api)

        assert_status_code(api.delete_current_user(headers=user.headers), 200)

        assert _count(db, "users", "id", user.user_id) == 0
        assert _count(db, "user_sessions", "user_id", user.user_id) == 0
        # Сессия по прежнему X-Session-Id больше не проходит.
        assert_status_code(api.current_user(headers=user.headers), 401)

    def test_keeps_content_and_orphans_it_by_default(self, api, db):
        user, club_id, thread_id, comment_id = _seed_content(api)

        assert_status_code(api.delete_current_user(headers=user.headers), 200)

        # Контент сохранён, но отвязан от удалённого пользователя.
        assert _count(db, "book_clubs", "id", club_id) == 1
        assert _count(db, "threads", "id", thread_id) == 1
        assert _count(db, "comments", "id", comment_id) == 1
        assert _count(db, "book_clubs", "owner_id", user.user_id) == 0
        assert _count(db, "threads", "author_id", user.user_id) == 0
        assert _count(db, "comments", "author_id", user.user_id) == 0

    def test_delete_clubs_removes_club_with_threads_and_comments(self, api, db):
        user, club_id, thread_id, comment_id = _seed_content(api)

        assert_status_code(
            api.delete_current_user(headers=user.headers, params={"delete_clubs": True}), 200
        )

        # Удаление клуба каскадит на его треды и комменты.
        assert _count(db, "book_clubs", "id", club_id) == 0
        assert _count(db, "threads", "id", thread_id) == 0
        assert _count(db, "comments", "id", comment_id) == 0

    def test_delete_threads_removes_threads_but_keeps_club(self, api, db):
        user, club_id, thread_id, comment_id = _seed_content(api)

        assert_status_code(
            api.delete_current_user(headers=user.headers, params={"delete_threads": True}), 200
        )

        assert _count(db, "book_clubs", "id", club_id) == 1
        assert _count(db, "threads", "id", thread_id) == 0
        assert _count(db, "comments", "id", comment_id) == 0

    def test_delete_comments_removes_comments_only(self, api, db):
        user, club_id, thread_id, comment_id = _seed_content(api)

        assert_status_code(
            api.delete_current_user(headers=user.headers, params={"delete_comments": True}), 200
        )

        assert _count(db, "book_clubs", "id", club_id) == 1
        assert _count(db, "threads", "id", thread_id) == 1
        assert _count(db, "comments", "id", comment_id) == 0
