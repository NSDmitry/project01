from sqlalchemy import select

from service.main import BATCH_LIMIT
from service.models import Delivery
from service.settings import settings

TOKEN_HEADER = {"X-Internal-Token": settings.internal_token}


def _item(event_id: int = 1, chat_id: int = 111, text: str = "Проверка") -> dict:
    return {"event_id": event_id, "telegram_chat_id": chat_id, "text": text}


def _rows(db):
    return db.execute(select(Delivery).order_by(Delivery.event_id)).scalars().all()


class TestBatchApi:
    def test_health(self, client):
        assert client.get("/health").status_code == 200

    def test_batch_saved_and_202(self, client, db):
        response = client.post(
            "/v1/notifications:batch",
            json=[_item(1), _item(2, chat_id=222, text="Вторая")],
            headers=TOKEN_HEADER,
        )

        assert response.status_code == 202
        rows = _rows(db)
        assert [(row.event_id, row.chat_id, row.text) for row in rows] == [
            (1, 111, "Проверка"),
            (2, 222, "Вторая"),
        ]
        assert all(row.processed_at is None for row in rows)

    def test_repeated_batch_is_idempotent(self, client, db):
        batch = [_item(1), _item(2)]

        first = client.post("/v1/notifications:batch", json=batch, headers=TOKEN_HEADER)
        second = client.post("/v1/notifications:batch", json=batch, headers=TOKEN_HEADER)

        assert first.status_code == 202
        assert second.status_code == 202
        assert len(_rows(db)) == 2

    def test_missing_token_401(self, client, db):
        response = client.post("/v1/notifications:batch", json=[_item()])

        assert response.status_code == 401
        assert _rows(db) == []

    def test_wrong_token_401(self, client, db):
        response = client.post(
            "/v1/notifications:batch", json=[_item()], headers={"X-Internal-Token": "wrong"}
        )

        assert response.status_code == 401
        assert _rows(db) == []

    def test_invalid_item_422_saves_nothing(self, client, db):
        # Один валидный элемент + один без text: батч атомарен, не сохраняется ничего.
        response = client.post(
            "/v1/notifications:batch",
            json=[_item(1), {"event_id": 2, "telegram_chat_id": 222}],
            headers=TOKEN_HEADER,
        )

        assert response.status_code == 422
        assert _rows(db) == []

    def test_oversized_batch_422(self, client, db):
        batch = [_item(event_id) for event_id in range(1, BATCH_LIMIT + 2)]

        response = client.post("/v1/notifications:batch", json=batch, headers=TOKEN_HEADER)

        assert response.status_code == 422
        assert _rows(db) == []
