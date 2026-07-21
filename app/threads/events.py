from app.core import events
from app.threads.repository import ThreadRepository


@events.subscribe(events.USER_DELETED, queue="threads")
async def on_user_deleted(payload: dict) -> None:
    async with events.session_factory() as db:
        threads_removed_by_club = await ThreadRepository(db).handle_user_deleted(
            payload["user_id"],
            delete_threads=payload["delete_threads"],
            delete_comments=payload["delete_comments"],
        )
        await db.commit()
    # Счётчики тредов ведёт домен клубов - сообщаем, сколько тредов автора ушло из
    # каждого клуба. Клубы удалённых владельцев чистит своим событием bookclubs.
    for club_id, count in threads_removed_by_club.items():
        await events.publish(events.THREAD_DELETED, {"club_id": club_id, "count": count})


@events.subscribe(events.CLUBS_DELETED, queue="threads")
async def on_clubs_deleted(payload: dict) -> None:
    async with events.session_factory() as db:
        await ThreadRepository(db).handle_clubs_deleted(payload["club_ids"])
        await db.commit()
