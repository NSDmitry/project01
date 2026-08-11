from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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
from app.core.media import media_url


class ClubMember(Base):
    __tablename__ = "club_members"
    __table_args__ = (
        # PK (club_id, user_id) обслуживает выборку по club_id (префикс), но не
        # по одному user_id: «мои клубы» и удаление пользователя.
        Index("ix_club_members_user_id", "user_id"),
        CheckConstraint("role IN ('member', 'moderator')", name="ck_club_members_role"),
    )

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Владельца здесь нет: он хранится в book_clubs.owner_id, и дублировать его
    # ролью значило бы завести второй источник правды, который может разъехаться.
    # Роль владельца в ответах выводится из owner_id.
    role: Mapped[str] = mapped_column(String, nullable=False, server_default="member")


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
    genre_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class BookClub(Base, DBLBase):
    __tablename__ = "book_clubs"
    __table_args__ = (
        # Фильтр «мои клубы» по владению и обнуление владельца при удалении пользователя.
        Index("ix_book_clubs_owner_id", "owner_id"),
        # Полнотекстовый поиск по клубам идёт по search_vector.
        Index("ix_book_clubs_search_vector", "search_vector", postgresql_using="gin"),
        CheckConstraint(
            "privacy IN ('public', 'by_request', 'by_invite')", name="ck_book_clubs_privacy"
        ),
    )

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    # Ключ файла в хранилище картинок (club-covers/<uuid>.webp). NULL - обложки нет.
    cover_key: Mapped[str | None] = mapped_column(String, nullable=True)
    # Как попасть в клуб: свободно, по одобренной заявке или по коду приглашения.
    # На видимость клуба в каталоге и поиске не влияет - иначе клуб «по заявке»
    # нельзя было бы найти, чтобы подать заявку.
    privacy: Mapped[str] = mapped_column(String, nullable=False, server_default="public")
    # NULL - владелец удалил аккаунт, не удаляя клуб. Обнуляет БД (ON DELETE SET NULL).
    owner_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Денормализованный счётчик тредов клуба. Треды - в другом домене,
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

    @property
    def cover_url(self) -> str | None:
        """Ссылка для ответов API - схемы собираются из модели по from_attributes."""
        return media_url(self.cover_key)


class ClubInvite(Base, DBLBase):
    """Код-приглашение в клуб: по нему вступают, минуя режим приватности."""
    __tablename__ = "club_invites"
    __table_args__ = (
        # FK не создаёт индекс на дочерней стороне: без него удаление клуба
        # сканирует таблицу приглашений целиком.
        Index("ix_club_invites_club_id", "club_id"),
        # То же для удаления пользователя (ON DELETE SET NULL по created_by).
        Index("ix_club_invites_created_by", "created_by"),
    )

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Уход создателя приглашение не отзывает: код выдан от имени клуба.
    # NULL - создатель удалил аккаунт, ставит БД (ON DELETE SET NULL).
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # NULL - код бессрочный. Иначе утёкшая ссылка живёт вечно, а закрытый клуб
    # перестаёт быть закрытым.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClubJoinRequest(Base, DBLBase):
    """Заявка на вступление в клуб с режимом «по заявке»."""
    __tablename__ = "club_join_requests"
    __table_args__ = (
        # Одна заявка на пару (клуб, пользователь): повторная подача переписывает
        # её статус, а не плодит строки. Ключ обслуживает и очередь заявок клуба
        # (club_id - префикс).
        UniqueConstraint("club_id", "user_id", name="uq_club_join_requests_club_id_user_id"),
        # Заявки удалённого пользователя чистятся по user_id.
        Index("ix_club_join_requests_user_id", "user_id"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_club_join_requests_status"
        ),
    )

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="pending")


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


class BookNomination(Base, DBLBase):
    """Книга, предложенная на следующий заход клуба."""
    __tablename__ = "book_nominations"
    __table_args__ = (
        # Одна книга номинируется в клубе один раз - иначе голоса за неё
        # разошлись бы по двум строкам. Ключ обслуживает и выборку номинаций
        # клуба (club_id - префикс).
        UniqueConstraint("club_id", "book_id", name="uq_book_nominations_club_id_book_id"),
    )

    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False
    )
    # Как у readings.book_id: удаление книги не должно уносить голосование.
    book_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("books.id", ondelete="SET NULL"), nullable=True
    )

    book = relationship("Book", lazy="selectin")


class NominationVote(Base):
    """Голос участника в голосовании клуба - один на клуб, переставляется."""
    __tablename__ = "nomination_votes"
    __table_args__ = (
        # Голоса клуба считаются одним запросом по club_id, а PK начинается с
        # user_id и как префикс его не покрывает. Без индекса этот подсчёт и
        # каскад при удалении клуба сканируют таблицу целиком.
        Index("ix_nomination_votes_club_id", "club_id"),
        # FK не создаёт индекс на дочерней стороне: без него удаление номинации
        # сканирует таблицу, чтобы выполнить каскад.
        Index("ix_nomination_votes_nomination_id", "nomination_id"),
    )

    # PK (user_id, club_id) - это и есть правило «один участник, один голос»:
    # держит его БД, а не проверка в коде. Голос за другую номинацию переписывает
    # ту же строку, поэтому счётчик не удваивается. user_id первым: по нему идёт
    # каскад при удалении пользователя, и префикс ключа его покрывает.
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_clubs.id", ondelete="CASCADE"), primary_key=True
    )
    nomination_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("book_nominations.id", ondelete="CASCADE"), nullable=False
    )


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
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Последний закрытый этап. NULL - участник отметил только страницу, а сопоставить
    # её с этапом не вышло (у этапов не заданы страницы).
    stage_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("reading_stages.id", ondelete="SET NULL"), nullable=True
    )
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
