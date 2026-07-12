"""create books and threads.book_id

Книги для обсуждений. books - справочник книг с собственным PK
(google_volume_id - уникальный внешний идентификатор Google Books для
дедупликации; NULL для книг, созданных пользователем вручную).
threads.book_id - опциональная привязка обсуждения к книге,
ON DELETE SET NULL, чтобы удаление книги не удаляло треды.

Все шаги защищены проверками наличия, чтобы миграция была идемпотентной.

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-12 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'books' not in inspector.get_table_names():
        op.create_table(
            'books',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('google_volume_id', sa.String(), nullable=True),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('author', sa.String(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('genres', sa.String(), nullable=True),
            sa.Column('published_year', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('google_volume_id'),
        )

    columns = [c['name'] for c in inspector.get_columns('threads')]
    if 'book_id' not in columns:
        op.add_column('threads', sa.Column('book_id', sa.BigInteger(), nullable=True))
        op.create_foreign_key(
            'fk_threads_book_id_books',
            'threads', 'books',
            ['book_id'], ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [c['name'] for c in inspector.get_columns('threads')]
    if 'book_id' in columns:
        op.drop_constraint('fk_threads_book_id_books', 'threads', type_='foreignkey')
        op.drop_column('threads', 'book_id')

    if 'books' in inspector.get_table_names():
        op.drop_table('books')
