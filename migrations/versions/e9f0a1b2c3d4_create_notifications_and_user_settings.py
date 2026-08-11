"""create notifications outbox and users.disabled_notifications

Уведомления без брокера: строка в notifications создаётся в той же транзакции,
что и породившее её событие (outbox), доставляет её по расписанию воркер
python -m app.notifications.tasks. user_id - CASCADE: очередь пользователя
живёт ровно столько, сколько он сам.

dedup_key - ключ идемпотентности напоминаний, генерируемых по расписанию
(дедлайны): повторный прогон не создаёт дубликат через ON CONFLICT DO NOTHING.
У событийных уведомлений он NULL, уникальность на NULL не срабатывает.

users.disabled_notifications - отключённые пользователем типы уведомлений,
по умолчанию пусто (все включены).

Revision ID: e9f0a1b2c3d4
Revises: b0c1d2e3f4a5
Create Date: 2026-08-11 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e9f0a1b2c3d4'
down_revision: Union[str, None] = 'b0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('text', sa.String(), nullable=False),
        sa.Column('dedup_key', sa.String(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], name='fk_notifications_user_id_users', ondelete='CASCADE'
        ),
        sa.UniqueConstraint('dedup_key', name='uq_notifications_dedup_key'),
    )
    # Скан воркера: только недоставленные строки, обработанные в индекс не попадают.
    op.create_index(
        'ix_notifications_pending',
        'notifications',
        ['id'],
        postgresql_where=sa.text('processed_at IS NULL'),
    )
    op.add_column(
        'users',
        sa.Column(
            'disabled_notifications',
            postgresql.ARRAY(sa.String()),
            server_default='{}',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'disabled_notifications')
    op.drop_index('ix_notifications_pending', table_name='notifications')
    op.drop_table('notifications')
