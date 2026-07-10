"""drop genre is_active

Колонка genres.is_active оказалась не нужна - клубы используют весь
справочник, флага активности жанра нет. Удаляем.

Idempotent: удаление под проверкой наличия колонки.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-10 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c['name'] for c in sa.inspect(bind).get_columns('genres')]
    if 'is_active' in columns:
        op.drop_column('genres', 'is_active')


def downgrade() -> None:
    bind = op.get_bind()
    columns = [c['name'] for c in sa.inspect(bind).get_columns('genres')]
    if 'is_active' not in columns:
        op.add_column(
            'genres',
            sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        )
