from sqlalchemy import select

from app.notifications.models import Notification
from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, ReadingFlow


def _rows(db) -> list[Notification]:
    db.expire_all()
    return db.execute(select(Notification).order_by(Notification.id)).scalars().all()


class TestNotificationOutbox:
    def test_comment_notifies_thread_author(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, title="Тред"), headers=owner.headers
        ).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        response = api.create_comment(thread_id, CommentFactory.create_payload(), headers=member.headers)

        assert_status_code(response, 201)
        rows = _rows(db)
        assert [(row.user_id, row.type) for row in rows] == [(owner.user_id, "comment_in_thread")]
        assert "Тред" in rows[0].text
        assert rows[0].processed_at is None

    def test_own_comment_is_not_announced(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        api.create_comment(thread_id, CommentFactory.create_payload(), headers=owner.headers)

        assert _rows(db) == []

    def test_reading_start_notifies_members_except_initiator(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        first = MemberFlow.join(api, club_id)
        second = MemberFlow.join(api, club_id)

        response = ReadingFlow.create(api, club_id, owner)

        assert_status_code(response, 201)
        rows = _rows(db)
        assert {row.user_id for row in rows} == {first.user_id, second.user_id}
        assert {row.type for row in rows} == {"reading_started"}
