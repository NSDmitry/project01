"""create comment_likes table

Лайки комментариев: одна строка - один лайк пользователя на комментарий,
дубли исключает уникальный ключ (comment_id, user_id). Оба FK - ON DELETE
CASCADE: лайк не имеет смысла ни без комментария, ни без пользователя
(в отличие от авторства, где author_id сохраняется через SET NULL).

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-03 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comment_likes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('comment_id', 'user_id', name='uq_comment_likes_comment_id_user_id'),
        sa.ForeignKeyConstraint(
            ['comment_id'], ['comments.id'], name='fk_comment_likes_comment_id_comments', ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], name='fk_comment_likes_user_id_users', ondelete='CASCADE'
        ),
    )


def downgrade() -> None:
    op.drop_table('comment_likes')
