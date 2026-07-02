"""rename discussions to threads

Переименование сущности discussions -> threads. Данные и структура столбцов не
меняются: переименовывается таблица и связанные с ней внешние ключи
(fk_discussions_* -> fk_threads_*), чтобы имена constraints соответствовали новой
таблице. Шаги защищены проверкой существующих constraints для идемпотентности.

Revision ID: f2a3b4c5d6e7
Revises: e5f6a7b8c9d0
Create Date: 2026-07-01 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table('discussions', 'threads')

    inspector = sa.inspect(op.get_bind())
    fks = {fk['name'] for fk in inspector.get_foreign_keys('threads')}
    if 'fk_discussions_club_id_book_clubs' in fks:
        op.execute(
            'ALTER TABLE threads RENAME CONSTRAINT fk_discussions_club_id_book_clubs '
            'TO fk_threads_club_id_book_clubs'
        )
    if 'fk_discussions_author_id_users' in fks:
        op.execute(
            'ALTER TABLE threads RENAME CONSTRAINT fk_discussions_author_id_users '
            'TO fk_threads_author_id_users'
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    fks = {fk['name'] for fk in inspector.get_foreign_keys('threads')}
    if 'fk_threads_author_id_users' in fks:
        op.execute(
            'ALTER TABLE threads RENAME CONSTRAINT fk_threads_author_id_users '
            'TO fk_discussions_author_id_users'
        )
    if 'fk_threads_club_id_book_clubs' in fks:
        op.execute(
            'ALTER TABLE threads RENAME CONSTRAINT fk_threads_club_id_book_clubs '
            'TO fk_discussions_club_id_book_clubs'
        )

    op.rename_table('threads', 'discussions')
