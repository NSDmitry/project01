"""replace members_ids array with club_members table

book_clubs.members_ids (ARRAY) денормализован: нет FK, нет ссылочной целостности,
а конкурентные join/leave гоняются на read-modify-write массива. Заменяем на
join-таблицу club_members (составной PK, FK с ON DELETE CASCADE). Существующее
членство переливается из массива перед удалением колонки.

Все шаги защищены проверками наличия, чтобы миграция была идемпотентной.

Revision ID: f1a2b3c4d5e6
Revises: c4d8e1f20a3b
Create Date: 2026-06-30 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'c4d8e1f20a3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'club_members' not in inspector.get_table_names():
        op.create_table(
            'club_members',
            sa.Column('club_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('club_id', 'user_id'),
        )

    columns = [c['name'] for c in inspector.get_columns('book_clubs')]
    if 'members_ids' in columns:
        op.execute(
            """
            INSERT INTO club_members (club_id, user_id)
            SELECT id, unnest(members_ids) FROM book_clubs
            ON CONFLICT DO NOTHING
            """
        )
        op.drop_column('book_clubs', 'members_ids')


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [c['name'] for c in inspector.get_columns('book_clubs')]
    if 'members_ids' not in columns:
        op.add_column(
            'book_clubs',
            sa.Column(
                'members_ids',
                postgresql.ARRAY(sa.Integer()),
                nullable=False,
                server_default='{}',
            ),
        )
        op.execute(
            """
            UPDATE book_clubs
            SET members_ids = COALESCE(
                (SELECT array_agg(user_id) FROM club_members WHERE club_members.club_id = book_clubs.id),
                '{}'
            )
            """
        )

    if 'club_members' in inspector.get_table_names():
        op.drop_table('club_members')
