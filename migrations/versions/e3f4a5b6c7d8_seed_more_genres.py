"""seed more genres

Пополнение каталога жанров. Отдельная миграция (не правка d2e3f4a5b6c7):
применяется обычным upgrade head и на локали, и на проде. Идемпотентно за счёт
ON CONFLICT (code) DO NOTHING.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-10 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (code, name, sort_order)
GENRES = [
    ('adventure', 'Приключения', 190),
    ('comics', 'Комиксы и графические романы', 200),
    ('dystopia', 'Антиутопия', 210),
    ('contemporary', 'Современная проза', 220),
    ('philosophy', 'Философия', 230),
]


def upgrade() -> None:
    genres = sa.table(
        'genres',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('sort_order', sa.Integer),
    )
    stmt = postgresql.insert(genres).values(
        [{'code': c, 'name': n, 'sort_order': s} for c, n, s in GENRES]
    )
    op.execute(stmt.on_conflict_do_nothing(index_elements=['code']))


def downgrade() -> None:
    codes = tuple(c for c, _, _ in GENRES)
    op.execute(
        sa.text("DELETE FROM genres WHERE code IN :codes").bindparams(
            sa.bindparam('codes', value=codes, expanding=True)
        )
    )
