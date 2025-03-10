"""fix

Revision ID: 4f3c8f3bbcdf
Revises: 3397e47a4db3
Create Date: 2025-03-10 16:08:04.546378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic.
revision: str = '4f3c8f3bbcdf'
down_revision: Union[str, None] = '3397e47a4db3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('book_clubs', sa.Column('members_ids', ARRAY(sa.Integer), nullable=False, server_default='{}'))


def downgrade() -> None:
    op.drop_column('book_clubs', 'members_ids')