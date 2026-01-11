from sqlalchemy import DateTime
from sqlalchemy.orm import Session

from app.core.errors.errors import NotFound
from app.db.models.db_user_session import DBUserSession


class UserSessionRepository:
    db: Session

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user_session(self, user_id: int, sid_hash: str, expires_at: DateTime) -> DBUserSession:
        session = DBUserSession()
        session.user_id = user_id
        session.sid_hash = sid_hash
        session.expires_at = expires_at

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def delete_user_session(self, sid_hash: str):
        session = self.db.query(DBUserSession).filter(DBUserSession.sid_hash == sid_hash).first()

        if session:
            self.db.delete(session)
            self.db.commit()
        else:
            raise NotFound("Сессия не найдена")

    def get_user_session(self, sid_hash: str) -> DBUserSession:
        return self.db.query(DBUserSession).filter(DBUserSession.sid_hash == sid_hash).first()