from app.bookclubs.repository import BookClubRepository
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
        # Счётчики тредов клубов правим той же транзакцией, что и удаление тредов.
        # Клубы удалённых владельцев bookclubs удаляет своим обработчиком.
        for club_id, count in threads_removed_by_club.items():
            await BookClubRepository(db).change_threads_count(club_id, -count)
        await db.commit()


@events.subscribe(events.CLUBS_DELETED, queue="threads")
async def on_clubs_deleted(payload: dict) -> None:
    async with events.session_factory() as db:
        await ThreadRepository(db).handle_clubs_deleted(payload["club_ids"])
        await db.commit()
