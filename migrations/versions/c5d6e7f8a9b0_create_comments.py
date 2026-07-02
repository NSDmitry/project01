"""create comments table

Комментарии к тредам: плоская лента без вложенности (нет parent_comment_id).
thread_id - ON DELETE CASCADE, комментарий не имеет смысла без треда (та же
логика, что у thread.club_id). author_id - ON DELETE SET NULL сразу при
создании таблицы, по аналогии с thread.author_id и book_club.owner_id, чтобы
удаление пользователя не блокировалось FK и не сносило чужие комментарии.

Revision ID: c5d6e7f8a9b0
Revises: b9c0d1e2f3a4
Create Date: 2026-07-02 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, None] = 'b9c0d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['thread_id'], ['threads.id'], name='fk_comments_thread_id_threads', ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['author_id'], ['users.id'], name='fk_comments_author_id_users', ondelete='SET NULL'
        ),
    )


def downgrade() -> None:
    op.drop_table('comments')
