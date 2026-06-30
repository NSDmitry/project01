"""create user_sessions

Revision ID: a1b2c3d4e5f6
Revises: 2cab341f7c55
Create Date: 2026-06-30 11:15:00.000000

Reconciles the `user_sessions` table into Alembic history. The table was
previously created only at runtime via Base.metadata.create_all (app/main.py,
app/db/database.py) and never had a migration. To stay safe in environments
where create_all already made the table, creation is guarded by has_table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '2cab341f7c55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table('user_sessions'):
        return
    op.create_table('user_sessions',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('sid_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('user_sessions')
