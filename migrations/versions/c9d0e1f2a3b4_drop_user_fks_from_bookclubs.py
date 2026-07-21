"""drop user FKs from bookclubs domain

Подготовка к выносу bookclubs в отдельный сервис: book_clubs.owner_id и
club_members.user_id больше не ссылаются FK-ом на users - клуб хранит только
id пользователя. SET NULL/CASCADE, которые раньше делала БД при удалении
пользователя, теперь выполняет код (BookClubRepository.handle_user_deleted).

Шаги защищены проверкой существующих constraints для идемпотентности.

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-07-20 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_user_fks(table: str) -> None:
    inspector = sa.inspect(op.get_bind())
    # у club_members FK создавался без явного имени - ищем по целевой таблице
    for fk in inspector.get_foreign_keys(table):
        if fk['referred_table'] == 'users':
            op.drop_constraint(fk['name'], table, type_='foreignkey')


def upgrade() -> None:
    _drop_user_fks('book_clubs')
    _drop_user_fks('club_members')


def downgrade() -> None:
    _drop_user_fks('book_clubs')
    _drop_user_fks('club_members')

    op.create_foreign_key(
        'fk_book_clubs_owner_id_users', 'book_clubs', 'users', ['owner_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'club_members_user_id_fkey', 'club_members', 'users', ['user_id'], ['id'], ondelete='CASCADE'
    )
