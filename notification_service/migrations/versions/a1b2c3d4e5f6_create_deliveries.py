"""create deliveries

Очередь доставки notification-service. Строки приходят батчами от relay
монолита, event_id (id строки outbox монолита) уникален - повторный батч
не создаёт дублей. Частичный индекс - скан воркера по недоставленным.

Все шаги защищены проверками наличия, чтобы миграция была идемпотентной.

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-08-12 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'deliveries' not in inspector.get_table_names():
        op.create_table(
            'deliveries',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('event_id', sa.BigInteger(), nullable=False),
            sa.Column('chat_id', sa.BigInteger(), nullable=False),
            sa.Column('text', sa.String(), nullable=False),
            sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
            sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('event_id'),
        )
        op.create_index(
            'ix_deliveries_pending',
            'deliveries',
            ['id'],
            postgresql_where=sa.text('processed_at IS NULL'),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'deliveries' in inspector.get_table_names():
        op.drop_table('deliveries')
