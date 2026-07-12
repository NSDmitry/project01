from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.db_base_model import DBLBase


class Thread(Base, DBLBase):
    __tablename__ = "threads"

    club_id = Column(BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)

    author = relationship("User", lazy="selectin")
    book = relationship("Book", lazy="selectin")


class Comment(Base, DBLBase):
    __tablename__ = "comments"

    thread_id = Column(BigInteger, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)

    author = relationship("User", lazy="selectin")


class CommentLike(Base, DBLBase):
    __tablename__ = "comment_likes"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_likes_comment_id_user_id"),
    )

    comment_id = Column(BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
