from app.bookclubs.repository import BookClubRepository
from app.core import events


@events.subscribe(events.USER_DELETED, queue="bookclubs")
async def on_user_deleted(payload: dict) -> None:
    async with events.session_factory() as db:
        deleted_club_ids = await BookClubRepository(db).handle_user_deleted(
            payload["user_id"], delete_owned_clubs=payload["delete_clubs"]
        )
        await db.commit()
    # Треды удалённых клубов чистит discussions - своим событием, не импортом.
    if deleted_club_ids:
        await events.publish(events.CLUBS_DELETED, {"club_ids": deleted_club_ids})
