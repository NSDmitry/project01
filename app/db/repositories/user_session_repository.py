from sqlalchemy import DateTime, or_
from sqlalchemy.orm import Session

from app.db.models.db_user_session import DBUserSession


class UserSessionRepository:
    db: Session

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user_session(self, user_id: int, sid_hash: str, last_used: DateTime) -> DBUserSession:
        session = DBUserSession()
        session.user_id = user_id
        session.sid_hash = sid_hash
        session.last_used = last_used

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def delete_user_session(self, sid_hash: str):
        session = self.db.query(DBUserSession).filter(DBUserSession.sid_hash == sid_hash).first()

        if session:
            self.db.delete(session)
            self.db.commit()

    def get_user_session(self, sid_hash: str) -> DBUserSession:
        return self.db.query(DBUserSession).filter(DBUserSession.sid_hash == sid_hash).first()

    def update_last_used(self, session: DBUserSession, last_used: DateTime) -> DBUserSession:
        session.last_used = last_used
        self.db.commit()

        return session

    def delete_all_user_sessions(self, user_id: int):
        self.db.query(DBUserSession).filter(DBUserSession.user_id == user_id).delete()
        self.db.commit()

    def delete_idle_sessions(self, cutoff: DateTime) -> int:
        deleted = self.db.query(DBUserSession).filter(
            or_(
                DBUserSession.last_used.is_(None),
                DBUserSession.last_used < cutoff,
            )
        ).delete(synchronize_session=False)
        self.db.commit()

        return deleted
