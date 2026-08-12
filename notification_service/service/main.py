import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from service.database import get_db
from service.models import Delivery
from service.settings import settings

app = FastAPI(title="notification-service")

BATCH_LIMIT = 500


class BatchItem(BaseModel):
    # id строки outbox монолита - ключ идемпотентности.
    event_id: int
    telegram_chat_id: int
    text: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/notifications:batch", status_code=202)
async def accept_batch(
    items: list[BatchItem],
    db: AsyncSession = Depends(get_db),
    x_internal_token: str = Header(""),
) -> None:
    # Пустой настроенный токен = приём закрыт (fail closed), а не открыт для всех.
    if not settings.internal_token or not secrets.compare_digest(
        x_internal_token, settings.internal_token
    ):
        raise HTTPException(status_code=401, detail="Неверный X-Internal-Token")

    if len(items) > BATCH_LIMIT:
        raise HTTPException(status_code=422, detail=f"Батч больше {BATCH_LIMIT} элементов")

    if not items:
        return

    # Идемпотентный приём: повтор батча (потерянный 202) гасится UNIQUE event_id.
    await db.execute(
        insert(Delivery)
        .values(
            [
                {"event_id": item.event_id, "chat_id": item.telegram_chat_id, "text": item.text}
                for item in items
            ]
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
