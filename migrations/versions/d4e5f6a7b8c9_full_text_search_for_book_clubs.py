"""full-text search for book clubs

Поиск клубов переезжает с ILIKE '%подстрока%' на полнотекстовый поиск Postgres.
Подстрочный поиск не умел ни словоформ («фантаст» не находил «фантастические»),
ни ранжирования - выдача сортировалась по id, то есть по дате создания.

search_vector - генерируемая колонка: Postgres пересчитывает её сам при любой
записи в name/description, поэтому ни триггера, ни поддержки в коде не нужно.
Вес A у названия, B у описания - совпадение в названии поднимается выше в
ts_rank.

Триграммные индексы удаляем: после перехода на FTS их никто не читает, а платить
за их поддержку на каждой записи клуба пришлось бы. Расширение pg_trgm при этом
остаётся - см. пояснение в b8c9d0e1f2a3.

ADD COLUMN ... GENERATED ALWAYS AS ... STORED переписывает таблицу под
ACCESS EXCLUSIVE. На нынешнем объёме book_clubs это доли секунды; если таблица
вырастет на порядки, колонку добавляют в три шага (обычная колонка, backfill
партиями, триггер), но городить это заранее смысла нет.

Revision ID: d4e5f6a7b8c9
Revises: b8c9d0e1f2a3
Create Date: 2026-08-10 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEARCH_VECTOR = """
    setweight(to_tsvector('russian', name), 'A') ||
    setweight(to_tsvector('russian', description), 'B')
"""

TRGM_INDEXES: Sequence[tuple[str, str]] = (
    ('ix_book_clubs_name_trgm', 'name'),
    ('ix_book_clubs_description_trgm', 'description'),
)


def upgrade() -> None:
    op.execute(
        f"ALTER TABLE book_clubs ADD COLUMN search_vector tsvector "
        f"GENERATED ALWAYS AS ({SEARCH_VECTOR}) STORED"
    )

    with op.get_context().autocommit_block():
        op.create_index(
            'ix_book_clubs_search_vector', 'book_clubs', ['search_vector'],
            postgresql_using='gin',
            postgresql_concurrently=True,
        )
        for name, _column in TRGM_INDEXES:
            op.drop_index(name, table_name='book_clubs', postgresql_concurrently=True)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, column in TRGM_INDEXES:
            op.create_index(
                name, 'book_clubs', [column],
                postgresql_using='gin',
                postgresql_ops={column: 'gin_trgm_ops'},
                postgresql_concurrently=True,
            )
        op.drop_index('ix_book_clubs_search_vector', table_name='book_clubs',
                      postgresql_concurrently=True)

    op.execute("ALTER TABLE book_clubs DROP COLUMN search_vector")
