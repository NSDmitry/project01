from sqlalchemy import BigInteger, String, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.db_base_model import DBLBase


class Thread(Base, DBLBase):
    __tablename__ = "threads"
    __table_args__ = (
        # Лента клуба: фильтр по club_id и сортировка по created_at/id одним
        # индексом - планировщику не нужен отдельный Sort.
        Index("ix_threads_club_id_created_at_id", "club_id", "created_at", "id"),
        # Треды автора: удаление или анонимизация пользователя.
        Index("ix_threads_author_id", "author_id"),
        # FK не создаёт индекс на дочерней стороне: без него удаление книги
        # сканирует threads целиком, чтобы выполнить ON DELETE SET NULL.
        Index("ix_threads_book_id", "book_id"),
    )

    # id клуба из bookclubs - без FK, треды удаляются кодом при удалении клуба
    club_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # id пользователя из iam - без FK, обнуляется кодом при удалении автора
    author_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    book_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("books.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Денормализованный счётчик комментариев треда. Комментарии в этом же домене,
    # поэтому столбец правится в той же транзакции - без событий.
    comments_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")

    book = relationship("Book", lazy="selectin")


class Comment(Base, DBLBase):
    __tablename__ = "comments"
    __table_args__ = (
        # Комментарии треда: фильтр и сортировка одним индексом.
        Index("ix_comments_thread_id_created_at_id", "thread_id", "created_at", "id"),
        # Комментарии автора: удаление или анонимизация пользователя.
        Index("ix_comments_author_id", "author_id"),
    )

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
        # Уникальный ключ обслуживает выборку по comment_id (префикс), но не по
        # одному user_id: удаление лайков при удалении пользователя.
        Index("ix_comment_likes_user_id", "user_id"),
    )

    comment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False
    )
    # id пользователя из iam - без FK, лайки удаляются кодом при удалении пользователя
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
