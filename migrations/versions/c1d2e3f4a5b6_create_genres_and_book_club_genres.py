"""create genres and book_club_genres

Жанры книжных клубов. genres - справочник (code/slug как стабильный
API-идентификатор, name для отображения). book_club_genres - join-таблица
клуб-жанр (составной PK, FK с ON DELETE CASCADE), повторяет club_members.

Все шаги защищены проверками наличия, чтобы миграция была идемпотентной.

Revision ID: c1d2e3f4a5b6
Revises: f8a9b0c1d2e3
Create Date: 2026-07-10 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'genres' not in tables:
        op.create_table(
            'genres',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('code', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code'),
        )

    if 'book_club_genres' not in tables:
        op.create_table(
            'book_club_genres',
            sa.Column('club_id', sa.BigInteger(), nullable=False),
            sa.Column('genre_id', sa.BigInteger(), nullable=False),
            sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['genre_id'], ['genres.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('club_id', 'genre_id'),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'book_club_genres' in tables:
        op.drop_table('book_club_genres')

    if 'genres' in tables:
        op.drop_table('genres')
