from service import worker
from service.models import Delivery
from service.worker import MAX_ATTEMPTS


def _add_delivery(db, event_id: int = 1, **overrides) -> int:
    delivery = Delivery(event_id=event_id, chat_id=111, text="Проверка", **overrides)
    db.add(delivery)
    db.commit()
    return delivery.id


def _row(db, delivery_id: int) -> Delivery:
    db.expire_all()
    return db.get(Delivery, delivery_id)


class TestDelivery:
    async def test_delivers_via_channel_and_marks_processed(self, db, async_db, monkeypatch):
        delivery_id = _add_delivery(db)

        sent = []

        async def fake_channel(chat_id, text):
            sent.append((chat_id, text))
            return True

        monkeypatch.setattr(worker, "CHANNELS", [fake_channel])

        delivered = await worker.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 1
        assert sent == [(111, "Проверка")]
        assert _row(db, delivery_id).processed_at is not None

    async def test_failed_send_increments_attempts_and_stays_pending(self, db, async_db, monkeypatch):
        delivery_id = _add_delivery(db)

        async def failing_channel(chat_id, text):
            return False

        monkeypatch.setattr(worker, "CHANNELS", [failing_channel])

        delivered = await worker.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 0
        row = _row(db, delivery_id)
        assert row.processed_at is None
        assert row.attempts == 1

    async def test_exhausted_attempts_are_skipped(self, db, async_db, monkeypatch):
        delivery_id = _add_delivery(db, attempts=MAX_ATTEMPTS)

        async def exploding_channel(chat_id, text):
            raise AssertionError("исчерпавшая попытки строка не должна выбираться")

        monkeypatch.setattr(worker, "CHANNELS", [exploding_channel])

        delivered = await worker.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 0
        assert _row(db, delivery_id).processed_at is None

    async def test_inapplicable_channels_close_row(self, db, async_db, monkeypatch):
        # Ни один канал не применим (все вернули None) - строка закрывается без отправки.
        delivery_id = _add_delivery(db)

        async def inapplicable_channel(chat_id, text):
            return None

        monkeypatch.setattr(worker, "CHANNELS", [inapplicable_channel])

        delivered = await worker.deliver_pending(async_db)
        await async_db.commit()

        assert delivered == 0
        row = _row(db, delivery_id)
        assert row.processed_at is not None
        assert row.attempts == 0
