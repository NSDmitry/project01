"""unique constraint on book_clubs.name

Уникальность имени клуба переносится на уровень БД: раньше она проверялась в
сервисе через выборку всей таблицы (O(n) и гонка). Теперь это UNIQUE-constraint,
а сервис ловит IntegrityError.

Шаги защищены проверкой существующего constraint для идемпотентности.

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-06-30 18:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    constraints = {c['name'] for c in inspector.get_unique_constraints('book_clubs')}
    if 'uq_book_clubs_name' not in constraints:
        op.create_unique_constraint('uq_book_clubs_name', 'book_clubs', ['name'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    constraints = {c['name'] for c in inspector.get_unique_constraints('book_clubs')}
    if 'uq_book_clubs_name' in constraints:
        op.drop_constraint('uq_book_clubs_name', 'book_clubs', type_='unique')
