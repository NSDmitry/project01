from sqlalchemy import BigInteger, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.db_base_model import DBLBase


class Thread(Base, DBLBase):
    __tablename__ = "threads"

    # id клуба из bookclubs - без FK, треды удаляются кодом при удалении клуба
    club_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # id пользователя из iam - без FK, обнуляется кодом при удалении автора
    author_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    book_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("books.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    book = relationship("Book", lazy="selectin")


class Comment(Base, DBLBase):
    __tablename__ = "comments"

    thread_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    # id пользователя из iam - без FK, обнуляется кодом при удалении автора
    author_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class CommentLike(Base, DBLBase):
    __tablename__ = "comment_likes"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_likes_comment_id_user_id"),
    )

    comment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False
    )
    # id пользователя из iam - без FK, лайки удаляются кодом при удалении пользователя
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
