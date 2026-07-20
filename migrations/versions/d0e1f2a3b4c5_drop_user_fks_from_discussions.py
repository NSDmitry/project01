"""drop user FKs from discussions domain

Продолжение развязки доменов от users (после c9d0e1f2a3b4 для bookclubs):
threads.author_id, comments.author_id и comment_likes.user_id больше не
ссылаются FK-ом на users - хранится только id. SET NULL/CASCADE, которые
раньше делала БД при удалении пользователя, теперь выполняет код
(ThreadRepository.handle_user_deleted).

Шаги защищены проверкой существующих constraints для идемпотентности.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-20 11:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ('threads', 'comments', 'comment_likes')


def _drop_user_fks(table: str) -> None:
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys(table):
        if fk['referred_table'] == 'users':
            op.drop_constraint(fk['name'], table, type_='foreignkey')


def upgrade() -> None:
    for table in TABLES:
        _drop_user_fks(table)


def downgrade() -> None:
    for table in TABLES:
        _drop_user_fks(table)

    op.create_foreign_key(
        'fk_threads_author_id_users', 'threads', 'users', ['author_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_comments_author_id_users', 'comments', 'users', ['author_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_comment_likes_user_id_users', 'comment_likes', 'users', ['user_id'], ['id'], ondelete='CASCADE'
    )
