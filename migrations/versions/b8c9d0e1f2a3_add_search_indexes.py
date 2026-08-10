"""add trigram and genre indexes for club search

Поиск клубов идёт по ILIKE '%подстрока%' - btree такой предикат не обслуживает
(ведущий процент), и до этой ревизии count и выборка читали book_clubs целиком.

Триграммный GIN закрывает подстроку, но сам по себе он бесполезен: пока все три
условия поиска стоят в одном OR, ветка с подзапросом по жанрам не индексируется,
и планировщик выбирает Seq Scan на весь запрос, не трогая GIN. Индексы работают
только вместе с UNION-формой запроса в BookClubRepository.get_book_clubs -
менять их порознь смысла нет.

Третий индекс - на book_club_genres.genre_id: PK (club_id, genre_id) обслуживает
выборку по club_id, а ветка поиска по жанрам фильтрует по второй колонке и шла
полным сканом связки.

pg_trgm - доверенное расширение с PostgreSQL 13, права владельца БД достаточно.

Индексы строятся CONCURRENTLY - см. пояснение в e4f5a6b7c8d9, включая порядок
действий, если построение сорвалось и остался индекс в состоянии INVALID.

Revision ID: b8c9d0e1f2a3
Revises: f5a6b7c8d9e0
Create Date: 2026-08-10 16:25:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRGM_INDEXES: Sequence[tuple[str, str]] = (
    ('ix_book_clubs_name_trgm', 'name'),
    ('ix_book_clubs_description_trgm', 'description'),
)


def upgrade() -> None:
    # CREATE EXTENSION в транзакции работает, а CONCURRENTLY - нет, поэтому
    # расширение ставим до autocommit_block.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    with op.get_context().autocommit_block():
        for name, column in TRGM_INDEXES:
            op.create_index(
                name, 'book_clubs', [column],
                postgresql_using='gin',
                postgresql_ops={column: 'gin_trgm_ops'},
                postgresql_concurrently=True,
            )
        op.create_index(
            'ix_book_club_genres_genre_id', 'book_club_genres', ['genre_id'],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index('ix_book_club_genres_genre_id', table_name='book_club_genres',
                      postgresql_concurrently=True)
        for name, _column in reversed(TRGM_INDEXES):
            op.drop_index(name, table_name='book_clubs', postgresql_concurrently=True)

    # Расширение не удаляем: оно могло стоять до этой миграции и использоваться
    # чем-то ещё. DROP EXTENSION здесь снёс бы чужие индексы.
