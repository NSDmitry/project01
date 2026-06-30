"""drop expires_at from user_sessions

Session liveness is governed solely by last_used (idle window); expires_at was
set at creation but never read. Drop is guarded by column presence so it is safe
to run where the column is already gone.

Revision ID: c4d8e1f20a3b
Revises: b3f7c2a91d04
Create Date: 2026-06-30 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8e1f20a3b'
down_revision: Union[str, None] = 'b3f7c2a91d04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c['name'] for c in sa.inspect(bind).get_columns('user_sessions')]
    if 'expires_at' not in columns:
        return
    op.drop_column('user_sessions', 'expires_at')


def downgrade() -> None:
    bind = op.get_bind()
    columns = [c['name'] for c in sa.inspect(bind).get_columns('user_sessions')]
    if 'expires_at' in columns:
        return
    op.add_column('user_sessions', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
