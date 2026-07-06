"""rename threads id sequence discussions_id_seq -> threads_id_seq

Таблицу discussions переименовали в threads (миграция f2a3b4c5d6e7), но
ALTER TABLE RENAME не переименовывает связанную SERIAL-последовательность -
она осталась discussions_id_seq. Приводим имя в соответствие с таблицей.

Rename безопасен: default колонки threads.id хранит ссылку на последовательность
по OID (nextval('...'::regclass)), а не по тексту, поэтому автоматически следует
за переименованием; owned-by связь тоже сохраняется. В коде имя последовательности
нигде не захардкожено.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-06 12:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER SEQUENCE discussions_id_seq RENAME TO threads_id_seq')


def downgrade() -> None:
    op.execute('ALTER SEQUENCE threads_id_seq RENAME TO discussions_id_seq')
