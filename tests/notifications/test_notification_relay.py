from sqlalchemy import select

from app.iam.models import User
from app.notifications import tasks
from app.notifications.models import Notification
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


async def _exploding_post(batch):
    raise AssertionError("сервис не должен вызываться: батч пуст")


class TestNotificationRelay:
    async def test_accepted_batch_closes_rows(self, api, db, async_db, monkeypatch):
        auth = AuthFlow.register(api)
        _bind_telegram(db, auth.user_id)
        notification_id = _add_notification(db, auth.user_id)

        batches = []

        async def accepting_post(batch):
            batches.append(batch)
            return True

        monkeypatch.setattr(tasks, "_post_batch", accepting_post)

        relayed = await tasks.relay_pending(async_db)
        await async_db.commit()

        assert relayed == 1
        assert batches == [
            [
                {
                    "event_id": notification_id,
                    "telegram_chat_id": 100_000 + auth.user_id,
                    "text": "Проверка",
                }
            ]
        ]
        assert _row(db, notification_id).processed_at is not None

    async def test_unavailable_service_keeps_rows_in_outbox(self, api, db, async_db, monkeypatch):
        auth = AuthFlow.register(api)
        _bind_telegram(db, auth.user_id)
        notification_id = _add_notification(db, auth.user_id)

        async def failing_post(batch):
            return False

        monkeypatch.setattr(tasks, "_post_batch", failing_post)

        relayed = await tasks.relay_pending(async_db)
        await async_db.commit()

        assert relayed == 0
        assert _row(db, notification_id).processed_at is None

    async def test_disabled_type_closed_without_send(self, api, db, async_db, monkeypatch):
        auth = AuthFlow.register(api)
        _bind_telegram(db, auth.user_id)
        api.update_notification_settings({"disabled": ["comment_in_thread"]}, headers=auth.headers)
        notification_id = _add_notification(db, auth.user_id)

        monkeypatch.setattr(tasks, "_post_batch", _exploding_post)

        relayed = await tasks.relay_pending(async_db)
        await async_db.commit()

        assert relayed == 0
        assert _row(db, notification_id).processed_at is not None

    async def test_user_without_channel_closed_without_send(self, api, db, async_db, monkeypatch):
        # Нет привязки Telegram - единственного канала: ждать нечего, строка закрывается.
        auth = AuthFlow.register(api)
        notification_id = _add_notification(db, auth.user_id)

        monkeypatch.setattr(tasks, "_post_batch", _exploding_post)

        relayed = await tasks.relay_pending(async_db)
        await async_db.commit()

        assert relayed == 0
        row = _row(db, notification_id)
        assert row.processed_at is not None
        assert row.attempts == 0
