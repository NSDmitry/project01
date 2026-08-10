from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class Reading(Base, DBLBase):
    """Заход клуба: книга, сроки и этапы, по которым сверяется прогресс участников."""
    __tablename__ = "readings"
    __table_args__ = (
        # Архив заходов клуба: фильтр по club_id и сортировка по id одним индексом.
        Index("ix_readings_club_id_id", "club_id", "id"),
        # «Текущий заход» - тот, что не закрыт. Двух таких у клуба быть не может,
        # и это держит БД, а не проверка в коде: две параллельные попытки создать
        # заход иначе обе прошли бы через SELECT и обе вставили строку.
        Index(
            "uq_readings_active_club_id",
            "club_id",
            unique=True,
            postgresql_where=text("finished_at IS NULL"),
        ),
    )

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False
    )
    # Книга из домена books. FK как у threads.book_id: удаление книги не должно
    # уносить историю чтения клуба.
    book_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("books.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    # NULL - заход идёт. Непустое значение переводит его в архив.
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    book = relationship("Book", lazy="selectin")


class ReadingStage(Base, DBLBase):
    """Этап захода: часть книги (главы или страницы) со своей датой."""
    __tablename__ = "reading_stages"
    __table_args__ = (
        # Уникальный ключ обслуживает и выборку этапов захода (reading_id - префикс).
        UniqueConstraint("reading_id", "position", name="uq_reading_stages_reading_id_position"),
    )

    reading_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("readings.id", ondelete="CASCADE"), nullable=False
    )
    # Порядковый номер этапа, начиная с 1. По нему сравнивается прогресс: участник
    # в графике, если закрыл этап не ниже того, чья дата уже наступила.
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Последняя страница этапа. NULL - этап задан главами, прогресс по номеру
    # страницы к нему не привязать.
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReadingProgress(Base, DBLBase):
    """Прогресс одного участника в заходе - последний закрытый этап и страница."""
    __tablename__ = "reading_progress"
    __table_args__ = (
        # Один участник - одна строка прогресса на заход. Ключ обслуживает и
        # выборку прогресса захода (reading_id - префикс).
        UniqueConstraint("reading_id", "user_id", name="uq_reading_progress_reading_id_user_id"),
        # Удаление пользователя и выход из клуба чистят прогресс по user_id.
        Index("ix_reading_progress_user_id", "user_id"),
        # FK не создаёт индекс на дочерней стороне: без него удаление этапа
        # сканирует таблицу целиком, чтобы выполнить ON DELETE SET NULL.
        Index("ix_reading_progress_stage_id", "stage_id"),
    )

    reading_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("readings.id", ondelete="CASCADE"), nullable=False
    )
    # id пользователя из iam - без FK, домены связаны только идентификатором
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Последний закрытый этап. NULL - участник отметил только страницу, а сопоставить
    # её с этапом не вышло (у этапов не заданы страницы).
    stage_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("reading_stages.id", ondelete="SET NULL"), nullable=True
    )
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
