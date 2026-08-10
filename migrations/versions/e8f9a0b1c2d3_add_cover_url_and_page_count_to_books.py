"""add cover_url and page_count to books

Google Books отдаёт обложку и число страниц в том же ответе, который уже
разбирается при поиске. Оба поля необязательные: книга может быть заведена
вручную, а Google может не отдать данные.

Бэкфилла нет: книга читается из БД по volume_id и в Google повторно не ходит,
так что у книг, сохранённых до миграции, поля останутся пустыми навсегда.
Дозаполнение - отдельной джобой, когда обложки понадобятся и для старых книг.

Revision ID: e8f9a0b1c2d3
Revises: d4e5f6a7b8c9
Create Date: 2026-08-10 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('books', sa.Column('cover_url', sa.String(), nullable=True))
    op.add_column('books', sa.Column('page_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('books', 'page_count')
    op.drop_column('books', 'cover_url')
