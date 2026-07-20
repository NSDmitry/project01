from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.db_base_model import DBLBase


class Thread(Base, DBLBase):
    __tablename__ = "threads"

    # id клуба из bookclubs - без FK, треды удаляются кодом при удалении клуба
    club_id = Column(BigInteger, nullable=False)
    # id пользователя из iam - без FK, обнуляется кодом при удалении автора
    author_id = Column(BigInteger, nullable=True)
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)

    book = relationship("Book", lazy="selectin")


class Comment(Base, DBLBase):
    __tablename__ = "comments"

    thread_id = Column(BigInteger, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    # id пользователя из iam - без FK, обнуляется кодом при удалении автора
    author_id = Column(BigInteger, nullable=True)
    content = Column(Text, nullable=False)


class CommentLike(Base, DBLBase):
    __tablename__ = "comment_likes"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_likes_comment_id_user_id"),
    )

    comment_id = Column(BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    # id пользователя из iam - без FK, лайки удаляются кодом при удалении пользователя
    user_id = Column(BigInteger, nullable=False)
