"""club cover and user avatar keys

Обложка клуба и аватар пользователя. В БД лежит только ключ файла в хранилище
картинок (club-covers/<uuid>.webp, avatars/<uuid>.webp), сами файлы - вне базы,
в S3-совместимом хранилище. Полный URL не храним: он зависит от того, как
приложение выставлено наружу, и при переезде пришлось бы переписывать все строки.

NULL - картинки нет; у всех существующих клубов и пользователей так и будет.

Revision ID: a1b2c3d4e5f7
Revises: f9a0b1c2d3e4
Create Date: 2026-08-11 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'f9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('book_clubs', sa.Column('cover_key', sa.String(), nullable=True))
    op.add_column('users', sa.Column('avatar_key', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_key')
    op.drop_column('book_clubs', 'cover_key')
