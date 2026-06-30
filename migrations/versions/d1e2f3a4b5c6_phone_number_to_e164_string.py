"""phone_number to e164 string

Revision ID: d1e2f3a4b5c6
Revises: c3d4e5f6a7b8
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'users', 'phone_number',
        existing_type=sa.BigInteger(),
        type_=sa.String(),
        existing_nullable=True,
        postgresql_using="'+' || phone_number::text",
    )


def downgrade() -> None:
    op.alter_column(
        'users', 'phone_number',
        existing_type=sa.String(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using="ltrim(phone_number, '+')::bigint",
    )
