"""drop telegram columns from users

Авторизация через Telegram удалена (не используется и не проверяла подпись).
Удаляем неиспользуемые колонки users.telegram_id и users.is_telegram_user.
UNIQUE-constraint на telegram_id уходит вместе с колонкой.

Шаги защищены проверкой наличия колонок для идемпотентности.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-30 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = [c['name'] for c in sa.inspect(op.get_bind()).get_columns('users')]
    if 'is_telegram_user' in columns:
        op.drop_column('users', 'is_telegram_user')
    if 'telegram_id' in columns:
        op.drop_column('users', 'telegram_id')


def downgrade() -> None:
    columns = [c['name'] for c in sa.inspect(op.get_bind()).get_columns('users')]
    if 'telegram_id' not in columns:
        op.add_column('users', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
        op.create_unique_constraint('users_telegram_id_key', 'users', ['telegram_id'])
    if 'is_telegram_user' not in columns:
        op.add_column('users', sa.Column('is_telegram_user', sa.Boolean(), nullable=True))
