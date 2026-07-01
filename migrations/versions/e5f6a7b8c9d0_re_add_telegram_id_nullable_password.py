"""re-add telegram_id and make password nullable

Telegram Mini App авторизация: возвращаем колонку users.telegram_id
(UNIQUE, nullable) и снимаем NOT NULL с users.password, так как
учётная запись, созданная через Telegram, не имеет пароля.

Revision ID: e5f6a7b8c9d0
Revises: d1e2f3a4b5c6
Create Date: 2026-07-01 01:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
    op.create_unique_constraint('users_telegram_id_key', 'users', ['telegram_id'])
    op.alter_column('users', 'password',
               existing_type=sa.String(),
               nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'password',
               existing_type=sa.String(),
               nullable=False)
    op.drop_constraint('users_telegram_id_key', 'users', type_='unique')
    op.drop_column('users', 'telegram_id')
