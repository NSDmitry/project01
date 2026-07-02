"""thread author_id ON DELETE SET NULL

Убираем асимметрию FK у threads: club_id уже был ON DELETE CASCADE, а author_id
блокировал удаление пользователя (NO ACTION). Делаем author_id nullable и
пересоздаём FK как ON DELETE SET NULL - удаление автора сохраняет тред, обнуляя
ссылку на автора.

Шаги защищены проверкой существующих constraints для идемпотентности.

Revision ID: a8b9c0d1e2f3
Revises: f2a3b4c5d6e7
Create Date: 2026-07-01 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    thread_fks = {fk['name'] for fk in inspector.get_foreign_keys('threads')}
    if 'fk_threads_author_id_users' in thread_fks:
        op.drop_constraint('fk_threads_author_id_users', 'threads', type_='foreignkey')

    op.alter_column('threads', 'author_id', existing_type=sa.Integer(), nullable=True)

    op.create_foreign_key(
        'fk_threads_author_id_users', 'threads', 'users', ['author_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    thread_fks = {fk['name'] for fk in inspector.get_foreign_keys('threads')}
    if 'fk_threads_author_id_users' in thread_fks:
        op.drop_constraint('fk_threads_author_id_users', 'threads', type_='foreignkey')

    op.alter_column('threads', 'author_id', existing_type=sa.Integer(), nullable=False)

    op.create_foreign_key('fk_threads_author_id_users', 'threads', 'users', ['author_id'], ['id'])
