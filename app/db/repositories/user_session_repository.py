from sqlalchemy import DateTime
from sqlalchemy.orm import Session
from app.db.models.db_user_session import DBUserSession


class UserSessionRepository:
    db: Session

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user_session(self, user_id: int, sid_hash: str, expires_at: DateTime) -> DBUserSession:
        user_session = DBUserSession(
            user_id=user_id,
            sid_hash=sid_hash,
            expires_at=expires_at
        )

        self.db.add(user_session)
        self.db.commit()
        self.db.refresh(user_session)

        return user_session

    def get_user_session(self, sid_hash: str) -> DBUserSession:
        return self.db.query(DBUserSession).filter(DBUserSession.sid_hash == sid_hash).first()