"""add foreign keys for owner, author and discussion club

Раньше owner_id / author_id / club_id были обычными Integer без ссылочной
целостности. Добавляем FK: book_clubs.owner_id -> users, discussions.author_id
-> users, discussions.club_id -> book_clubs (ON DELETE CASCADE, чтобы удаление
клуба убирало его обсуждения, а не оставляло сиротами).

Шаги защищены проверкой существующих constraints для идемпотентности.

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-06-30 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    book_fks = {fk['name'] for fk in inspector.get_foreign_keys('book_clubs')}
    if 'fk_book_clubs_owner_id_users' not in book_fks:
        op.create_foreign_key('fk_book_clubs_owner_id_users', 'book_clubs', 'users', ['owner_id'], ['id'])

    discussion_fks = {fk['name'] for fk in inspector.get_foreign_keys('discussions')}
    if 'fk_discussions_club_id_book_clubs' not in discussion_fks:
        op.create_foreign_key(
            'fk_discussions_club_id_book_clubs', 'discussions', 'book_clubs', ['club_id'], ['id'], ondelete='CASCADE'
        )
    if 'fk_discussions_author_id_users' not in discussion_fks:
        op.create_foreign_key('fk_discussions_author_id_users', 'discussions', 'users', ['author_id'], ['id'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    discussion_fks = {fk['name'] for fk in inspector.get_foreign_keys('discussions')}
    if 'fk_discussions_author_id_users' in discussion_fks:
        op.drop_constraint('fk_discussions_author_id_users', 'discussions', type_='foreignkey')
    if 'fk_discussions_club_id_book_clubs' in discussion_fks:
        op.drop_constraint('fk_discussions_club_id_book_clubs', 'discussions', type_='foreignkey')

    book_fks = {fk['name'] for fk in inspector.get_foreign_keys('book_clubs')}
    if 'fk_book_clubs_owner_id_users' in book_fks:
        op.drop_constraint('fk_book_clubs_owner_id_users', 'book_clubs', type_='foreignkey')
