from app.core import events
from app.threads.repository import ThreadRepository


@events.subscribe(events.USER_DELETED, queue="threads")
async def on_user_deleted(payload: dict) -> None:
    async with events.session_factory() as db:
        await ThreadRepository(db).handle_user_deleted(
            payload["user_id"],
            delete_threads=payload["delete_threads"],
            delete_comments=payload["delete_comments"],
        )
        await db.commit()


@events.subscribe(events.CLUBS_DELETED, queue="threads")
async def on_clubs_deleted(payload: dict) -> None:
    async with events.session_factory() as db:
        await ThreadRepository(db).handle_clubs_deleted(payload["club_ids"])
        await db.commit()
