"""book_club owner_id ON DELETE SET NULL

По аналогии с threads.author_id убираем асимметрию FK у book_clubs: owner_id
блокировал удаление пользователя (NO ACTION). Делаем owner_id nullable и
пересоздаём FK как ON DELETE SET NULL - удаление владельца сохраняет клуб,
обнуляя ссылку на владельца.

Шаги защищены проверкой существующих constraints для идемпотентности.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-07-01 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c0d1e2f3a4'
down_revision: Union[str, None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    book_fks = {fk['name'] for fk in inspector.get_foreign_keys('book_clubs')}
    if 'fk_book_clubs_owner_id_users' in book_fks:
        op.drop_constraint('fk_book_clubs_owner_id_users', 'book_clubs', type_='foreignkey')

    op.alter_column('book_clubs', 'owner_id', existing_type=sa.Integer(), nullable=True)

    op.create_foreign_key(
        'fk_book_clubs_owner_id_users', 'book_clubs', 'users', ['owner_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    book_fks = {fk['name'] for fk in inspector.get_foreign_keys('book_clubs')}
    if 'fk_book_clubs_owner_id_users' in book_fks:
        op.drop_constraint('fk_book_clubs_owner_id_users', 'book_clubs', type_='foreignkey')

    op.alter_column('book_clubs', 'owner_id', existing_type=sa.Integer(), nullable=False)

    op.create_foreign_key('fk_book_clubs_owner_id_users', 'book_clubs', 'users', ['owner_id'], ['id'])
