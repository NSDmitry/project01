from sqlalchemy import DateTime, or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.db_user_session import DBUserSession


class UserSessionRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user_session(self, user_id: int, sid_hash: str, last_used: DateTime) -> DBUserSession:
        session = DBUserSession()
        session.user_id = user_id
        session.sid_hash = sid_hash
        session.last_used = last_used

        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        return session

    async def delete_user_session(self, sid_hash: str):
        result = await self.db.execute(select(DBUserSession).where(DBUserSession.sid_hash == sid_hash))
        session = result.scalar_one_or_none()

        if session:
            await self.db.delete(session)
            await self.db.flush()

    async def get_user_session(self, sid_hash: str) -> DBUserSession:
        result = await self.db.execute(select(DBUserSession).where(DBUserSession.sid_hash == sid_hash))

        return result.scalar_one_or_none()

    async def update_last_used(self, session: DBUserSession, last_used: DateTime) -> DBUserSession:
        session.last_used = last_used
        await self.db.flush()

        return session

    async def delete_all_user_sessions(self, user_id: int):
        await self.db.execute(delete(DBUserSession).where(DBUserSession.user_id == user_id))
        await self.db.flush()

    async def delete_idle_sessions(self, cutoff: DateTime) -> int:
        result = await self.db.execute(
            delete(DBUserSession).where(
                or_(
                    DBUserSession.last_used.is_(None),
                    DBUserSession.last_used < cutoff,
                )
            )
        )
        await self.db.flush()

        return result.rowcount
