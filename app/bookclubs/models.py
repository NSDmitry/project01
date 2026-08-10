from sqlalchemy import BigInteger, Computed, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_base_model import DBLBase


class ClubMember(Base):
    __tablename__ = "club_members"
    __table_args__ = (
        # PK (club_id, user_id) обслуживает выборку по club_id (префикс), но не
        # по одному user_id: «мои клубы» и удаление пользователя.
        Index("ix_club_members_user_id", "user_id"),
    )

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True
    )
    # id пользователя из iam - без FK, домены связаны только идентификатором
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class BookClubGenre(Base):
    __tablename__ = "book_club_genres"
    __table_args__ = (
        # PK (club_id, genre_id) обслуживает выборку по club_id, но не по одному
        # genre_id: поиск клубов по жанру шёл полным сканом связки.
        Index("ix_book_club_genres_genre_id", "genre_id"),
    )

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True
    )
    # id жанра из genres - без FK, домены связаны только идентификатором
    genre_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class BookClub(Base, DBLBase):
    __tablename__ = "book_clubs"
    __table_args__ = (
        # Фильтр «мои клубы» по владению и обнуление владельца при удалении пользователя.
        Index("ix_book_clubs_owner_id", "owner_id"),
        # Полнотекстовый поиск по клубам идёт по search_vector.
        Index("ix_book_clubs_search_vector", "search_vector", postgresql_using="gin"),
    )

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    # id пользователя из iam - без FK, обнуляется кодом при удалении владельца
    owner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Денормализованный счётчик тредов клуба. Треды - в другом домене (без FK),
    # поэтому клуб не считает их подзапросом, а ведёт столбец по событиям
    # THREAD_CREATED/THREAD_DELETED (см. events.py).
    threads_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    # Денормализованный счётчик участников. В отличие от threads_count участники
    # живут в этом же домене, поэтому столбец правится в той же транзакции, что и
    # club_members - без событий и без риска разъехаться.
    members_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    # Генерируемая колонка - Postgres пересчитывает её сам при записи в
    # name/description, поддержки в коде не требуется. Вес A у названия, B у
    # описания: совпадение в названии весит больше при ранжировании.
    # deferred - в Python значение не читается никогда, в SELECT его тянуть незачем.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('russian', name), 'A') || "
            "setweight(to_tsvector('russian', description), 'B')",
            persisted=True,
        ),
        deferred=True,
    )
