"""widen int PKs and their references to BigInteger

Автоинкрементные PK создавались как SERIAL (int4) с потолком 2 147 483 647.
Расширяем их и все ссылающиеся на них колонки до BigInteger (int8), чтобы снять
потолок.

Важный нюанс: SERIAL создаёт последовательность "AS integer", и её максимум тоже
обрезан по int4 - независимо от типа колонки. Поэтому мало сменить тип колонки,
надо поднять и саму последовательность (ALTER SEQUENCE ... AS bigint), иначе
nextval() упрётся в int4 при живой bigint-колонке. Имя последовательности берём
через pg_get_serial_sequence, а не как <table>_id_seq: у threads оно осталось
discussions_id_seq после переименования таблицы (ALTER TABLE RENAME не трогает
имя последовательности).

FK-констрейнты дропать не требуется: int4 -> int8 это расширение, значения
остаются валидными, а обе стороны FK меняем на один тип.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-06 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Таблицы с автоинкрементным PK id (SERIAL).
PK_TABLES = ('users', 'book_clubs', 'threads', 'comments', 'comment_likes')

# Колонки, ссылающиеся на int-id: (таблица, колонка, nullable).
FK_COLUMNS = (
    ('user_sessions', 'user_id', False),
    ('club_members', 'club_id', False),
    ('club_members', 'user_id', False),
    ('book_clubs', 'owner_id', True),
    ('threads', 'club_id', False),
    ('threads', 'author_id', True),
    ('comments', 'thread_id', False),
    ('comments', 'author_id', True),
    ('comment_likes', 'comment_id', False),
    ('comment_likes', 'user_id', False),
)


def _resize_id_sequences(target_type: str) -> None:
    """Меняет тип последовательностей PK id на target_type ('bigint'/'integer').

    Имя резолвится через pg_get_serial_sequence, чтобы не зависеть от совпадения
    с <table>_id_seq (threads использует discussions_id_seq после переименования).
    """
    tables = ", ".join(f"'{t}'" for t in PK_TABLES)
    op.execute(
        f"""
        DO $$
        DECLARE
            tbl text;
            seq text;
        BEGIN
            FOREACH tbl IN ARRAY ARRAY[{tables}]
            LOOP
                seq := pg_get_serial_sequence(tbl, 'id');
                IF seq IS NOT NULL THEN
                    EXECUTE format('ALTER SEQUENCE %s AS {target_type}', seq);
                END IF;
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    for table in PK_TABLES:
        op.alter_column(
            table, 'id',
            existing_type=sa.Integer(), type_=sa.BigInteger(),
            existing_nullable=False,
        )

    _resize_id_sequences('bigint')

    for table, column, nullable in FK_COLUMNS:
        op.alter_column(
            table, column,
            existing_type=sa.Integer(), type_=sa.BigInteger(),
            existing_nullable=nullable,
        )


def downgrade() -> None:
    for table, column, nullable in FK_COLUMNS:
        op.alter_column(
            table, column,
            existing_type=sa.BigInteger(), type_=sa.Integer(),
            existing_nullable=nullable,
        )

    _resize_id_sequences('integer')

    for table in PK_TABLES:
        op.alter_column(
            table, 'id',
            existing_type=sa.BigInteger(), type_=sa.Integer(),
            existing_nullable=False,
        )
