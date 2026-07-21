"""drop book_clubs FK from threads

Последняя кросс-доменная связь на уровне БД: threads.club_id больше не
ссылается FK-ом на book_clubs - хранится только id. CASCADE при удалении
клуба теперь выполняет код (ThreadRepository.handle_clubs_deleted).

Шаги защищены проверкой существующих constraints для идемпотентности.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-20 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_club_fks() -> None:
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys('threads'):
        if fk['referred_table'] == 'book_clubs':
            op.drop_constraint(fk['name'], 'threads', type_='foreignkey')


def upgrade() -> None:
    _drop_club_fks()


def downgrade() -> None:
    _drop_club_fks()

    op.create_foreign_key(
        'fk_threads_club_id_book_clubs', 'threads', 'book_clubs', ['club_id'], ['id'], ondelete='CASCADE'
    )
