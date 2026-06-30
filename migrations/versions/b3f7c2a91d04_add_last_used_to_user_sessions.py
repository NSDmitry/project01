"""add last_used to user_sessions

Revision ID: b3f7c2a91d04
Revises: 2cab341f7c55
Create Date: 2026-06-30 11:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f7c2a91d04'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c['name'] for c in sa.inspect(bind).get_columns('user_sessions')]
    if 'last_used' in columns:
        return
    op.add_column('user_sessions', sa.Column('last_used', sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE user_sessions
        SET last_used = CASE
            WHEN now() >= expires_at THEN now()
            ELSE expires_at
        END
        """
    )


def downgrade() -> None:
    op.drop_column('user_sessions', 'last_used')
