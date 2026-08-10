"""add denormalized members_count and comments_count

Списочные ручки отдают Page.total, и до этой ревизии он считался через count(*)
на каждый запрос: участники клуба, комментарии треда и members_count каждого
клуба на странице каталога.

Стоимость такого count(*) растёт с размером коллекции (страница - нет) и, что
хуже, зависит от свежести visibility map: пока она свежая, Index Only Scan по
100k комментариев занимает ~10 мс, а после обычных UPDATE по таблице тот же план
вырождается в 100k heap fetches и полсекунды.

Оба счётчика - того же рода, что threads_count из d3e4f5a6b7c8, но проще: и
club_members, и comments лежат в одном домене со своим родителем, поэтому столбец
правится в той же транзакции, что и сама строка, а не по событию. Расхождение
возможно только при прямых правках в обход репозитория.

Бэкфилл считает текущее состояние одним проходом на таблицу.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-08-10 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'book_clubs',
        sa.Column('members_count', sa.BigInteger(), server_default='0', nullable=False),
    )
    op.add_column(
        'threads',
        sa.Column('comments_count', sa.BigInteger(), server_default='0', nullable=False),
    )

    # UPDATE ... FROM с группировкой, а не скалярный подзапрос на строку: один
    # проход по club_members/comments вместо одного запроса на каждого родителя.
    op.execute(
        "UPDATE book_clubs bc SET members_count = m.cnt "
        "FROM (SELECT club_id, count(*) AS cnt FROM club_members GROUP BY club_id) m "
        "WHERE bc.id = m.club_id"
    )
    op.execute(
        "UPDATE threads t SET comments_count = c.cnt "
        "FROM (SELECT thread_id, count(*) AS cnt FROM comments GROUP BY thread_id) c "
        "WHERE t.id = c.thread_id"
    )


def downgrade() -> None:
    op.drop_column('threads', 'comments_count')
    op.drop_column('book_clubs', 'members_count')
