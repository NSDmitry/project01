"""add threads_count to book_clubs

Денормализованный счётчик тредов клуба. Раньше BookClubService считал его
подзапросом через ThreadRepository (bookclubs -> threads). Треды уезжают в
отдельный сервис, обратной зависимости быть не должно: клуб ведёт свой столбец
по событиям THREAD_CREATED/THREAD_DELETED (BookClubRepository.change_threads_count).

Бэкфилл считает текущие треды по club_id - на момент миграции треды ещё в той же
БД. Значение допускает расхождение при потере события (в проде - reconcile-джоба).

Revision ID: d3e4f5a6b7c8
Revises: a9b0c1d2e3f4
Create Date: 2026-07-20 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'a9b0c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'book_clubs',
        sa.Column('threads_count', sa.BigInteger(), server_default='0', nullable=False),
    )
    op.execute(
        "UPDATE book_clubs bc SET threads_count = "
        "(SELECT count(*) FROM threads t WHERE t.club_id = bc.id)"
    )


def downgrade() -> None:
    op.drop_column('book_clubs', 'threads_count')
