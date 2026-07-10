"""seed genres

Курируемый стартовый список жанров книжных клубов. Наполнение ручное,
не автоген - список меняется как продуктовое решение. Идемпотентно за счёт
ON CONFLICT (code) DO NOTHING.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-10 16:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (code, name, sort_order)
GENRES = [
    ('fiction', 'Художественная литература', 10),
    ('non-fiction', 'Нон-фикшн', 20),
    ('classics', 'Классика', 30),
    ('sci-fi', 'Научная фантастика', 40),
    ('fantasy', 'Фэнтези', 50),
    ('detective', 'Детективы', 60),
    ('thriller', 'Триллеры', 70),
    ('horror', 'Ужасы', 80),
    ('romance', 'Любовные романы', 90),
    ('historical', 'Историческая проза', 100),
    ('biography', 'Биографии и мемуары', 110),
    ('poetry', 'Поэзия', 120),
    ('young-adult', 'Young Adult', 130),
    ('children', 'Детская литература', 140),
    ('business', 'Бизнес и финансы', 150),
    ('self-development', 'Саморазвитие', 160),
    ('science-popular', 'Научпоп', 170),
    ('psychology', 'Психология', 180),
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
