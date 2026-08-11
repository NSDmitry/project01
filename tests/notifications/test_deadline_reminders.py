from sqlalchemy import select

from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository
from tests.support.factories import ReadingFactory
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, ReadingFlow


def _rows(db) -> list[Notification]:
    db.expire_all()
    return db.execute(select(Notification).order_by(Notification.id)).scalars().all()


class TestDeadlineReminders:
    async def test_reminds_club_members_day_before(self, api, db, async_db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        # Дедлайн захода и единственного этапа - завтра.
        ReadingFlow.create(
            api, club_id, owner,
            ReadingFactory.payload(
                deadline_in_days=1,
                stages=[ReadingFactory.stage(title="Финал", due_in_days=1, end_page=100)],
            ),
        )

        await NotificationRepository(async_db).create_deadline_reminders()
        await async_db.commit()

        # Старт захода сам по себе кладёт участнику reading_started - здесь
        # интересны только напоминания о дедлайнах.
        rows = [row for row in _rows(db) if row.type.endswith("_deadline")]
        by_type = {type: {row.user_id for row in rows if row.type == type} for type in {r.type for r in rows}}
        # Напоминания получают все участники, включая владельца.
        assert by_type == {
            "stage_deadline": {owner.user_id, member.user_id},
            "reading_deadline": {owner.user_id, member.user_id},
        }
        assert "Финал" in next(row.text for row in rows if row.type == "stage_deadline")

    async def test_repeat_run_is_idempotent(self, api, db, async_db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        ReadingFlow.create(
            api, club_id, owner,
            ReadingFactory.payload(
                deadline_in_days=1,
                stages=[ReadingFactory.stage(title="Финал", due_in_days=1, end_page=100)],
            ),
        )

        repository = NotificationRepository(async_db)
        await repository.create_deadline_reminders()
        await async_db.commit()
        first_count = len(_rows(db))

        await repository.create_deadline_reminders()
        await async_db.commit()

        assert len(_rows(db)) == first_count

    async def test_far_deadlines_are_silent(self, api, db, async_db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        # Дефолтный заход: дедлайн через 10 дней, этапы вчера и через 5 дней.
        ReadingFlow.create(api, club_id, owner)

        await NotificationRepository(async_db).create_deadline_reminders()
        await async_db.commit()

        assert _rows(db) == []
