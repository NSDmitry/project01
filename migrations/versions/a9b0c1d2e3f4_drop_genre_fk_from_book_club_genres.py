"""drop genres FK from book_club_genres

Жанры уезжают в отдельный сервис: book_club_genres.genre_id больше не
ссылается FK-ом на genres - хранится только id. CASCADE при удалении жанра
теперь выполняет код (BookClubRepository.handle_genres_deleted по событию
GENRES_DELETED).

Шаги защищены проверкой существующих constraints для идемпотентности.

Revision ID: a9b0c1d2e3f4
Revises: e1f2a3b4c5d6
Create Date: 2026-07-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b0c1d2e3f4'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_genre_fks() -> None:
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys('book_club_genres'):
        if fk['referred_table'] == 'genres':
            op.drop_constraint(fk['name'], 'book_club_genres', type_='foreignkey')


def upgrade() -> None:
    _drop_genre_fks()


def downgrade() -> None:
    _drop_genre_fks()

    op.create_foreign_key(
        'fk_book_club_genres_genre_id_genres',
        'book_club_genres', 'genres', ['genre_id'], ['id'], ondelete='CASCADE',
    )
