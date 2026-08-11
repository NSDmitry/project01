from sqlalchemy import select

from app.iam.models import User
from app.notifications import tasks
from app.notifications.models import Notification
from app.notifications.repository import MAX_ATTEMPTS
from tests.support.flows import AuthFlow


def _add_notification(db, user_id: int, type: str = "comment_in_thread", **overrides) -> int:
    notification = Notification(user_id=user_id, type=type, text="Проверка", **overrides)
    db.add(notification)
    db.commit()
    return notification.id


def _row(db, notification_id: int) -> Notification:
    db.expire_all()
    return db.get(Notification, notification_id)


def _bind_telegram(db, user_id: int) -> None:
    db.execute(select(User).where(User.id == user_id)).scalar_one().telegram_id = 100_000 + user_id
    db.commit()


class TestNotificationDelivery:
    async def test_delivers_via_channel_and_marks_processed(self, api, db, async_db, monkeypatch):
        auth = AuthFlow.register(api)
        _bind_telegram(db, auth.user_id)
        notification_id = _add_notification(db, auth.user_id)

        sent = []

        async def fake_channel(user, text):
            sent.append((user.id, text))
            return True

        monkeypatch.setattr(tasks, "CHANNELS", [fake_channel])

        delivered = await tasks.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 1
        assert sent == [(auth.user_id, "Проверка")]
        assert _row(db, notification_id).processed_at is not None

    async def test_user_without_any_channel_marks_processed(self, api, db, async_db):
        # Реальный CHANNELS: у пользователя нет Telegram - send_telegram вернёт
        # None без похода в сеть, строка закрывается и отправку не ломает.
        auth = AuthFlow.register(api)
        notification_id = _add_notification(db, auth.user_id)

        delivered = await tasks.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 0
        row = _row(db, notification_id)
        assert row.processed_at is not None
        assert row.attempts == 0

    async def test_disabled_type_is_not_sent(self, api, db, async_db, monkeypatch):
        auth = AuthFlow.register(api)
        _bind_telegram(db, auth.user_id)
        api.update_notification_settings({"disabled": ["comment_in_thread"]}, headers=auth.headers)
        notification_id = _add_notification(db, auth.user_id)

        async def exploding_channel(user, text):
            raise AssertionError("канал не должен вызываться для отключённого типа")

        monkeypatch.setattr(tasks, "CHANNELS", [exploding_channel])

        delivered = await tasks.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 0
        assert _row(db, notification_id).processed_at is not None

    async def test_failed_send_increments_attempts_and_stays_pending(self, api, db, async_db, monkeypatch):
        auth = AuthFlow.register(api)
        _bind_telegram(db, auth.user_id)
        notification_id = _add_notification(db, auth.user_id)

        async def failing_channel(user, text):
            return False

        monkeypatch.setattr(tasks, "CHANNELS", [failing_channel])

        delivered = await tasks.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 0
        row = _row(db, notification_id)
        assert row.processed_at is None
        assert row.attempts == 1

    async def test_exhausted_attempts_are_skipped(self, api, db, async_db, monkeypatch):
        auth = AuthFlow.register(api)
        _bind_telegram(db, auth.user_id)
        notification_id = _add_notification(db, auth.user_id, attempts=MAX_ATTEMPTS)

        async def exploding_channel(user, text):
            raise AssertionError("исчерпавшая попытки строка не должна выбираться")

        monkeypatch.setattr(tasks, "CHANNELS", [exploding_channel])

        delivered = await tasks.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 0
        assert _row(db, notification_id).processed_at is None
