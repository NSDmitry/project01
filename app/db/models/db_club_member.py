from sqlalchemy import Column, Integer, ForeignKey

from app.db.database import Base


class DBClubMember(Base):
    __tablename__ = "club_members"

    club_id = Column(Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
