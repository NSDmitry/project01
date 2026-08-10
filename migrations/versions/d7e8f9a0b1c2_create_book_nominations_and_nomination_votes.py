"""create book_nominations and nomination_votes

Выбор следующей книги голосованием: участники предлагают книги, каждый отдаёт
один голос, владелец закрывает голосование и книга-победитель становится заходом.

book_nominations.club_id - CASCADE: голосование живёт ровно столько, сколько клуб.
book_id - SET NULL, как у readings.book_id: удаление книги не должно уносить
голосование. Уникальный ключ (club_id, book_id) не даёт номинировать одну книгу
дважды - иначе голоса за неё разошлись бы по двум кандидатам.

nomination_votes - PK (user_id, club_id): это и есть «один участник - один голос»,
держит его БД, а не проверка в коде. Голос за другую номинацию переписывает ту же
строку. user_id первым в ключе: по нему идёт чистка при удалении пользователя, и
префикс ключа её покрывает. FK на пользователя нет - он в другом домене.

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-08-10 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = 'c6d7e8f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'book_nominations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('club_id', sa.BigInteger(), nullable=False),
        sa.Column('book_id', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'book_id', name='uq_book_nominations_club_id_book_id'),
        sa.ForeignKeyConstraint(
            ['club_id'], ['book_clubs.id'], name='fk_book_nominations_club_id_book_clubs', ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['book_id'], ['books.id'], name='fk_book_nominations_book_id_books', ondelete='SET NULL'
        ),
    )

    op.create_table(
        'nomination_votes',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('club_id', sa.BigInteger(), nullable=False),
        sa.Column('nomination_id', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'club_id'),
        sa.ForeignKeyConstraint(
            ['club_id'], ['book_clubs.id'], name='fk_nomination_votes_club_id_book_clubs', ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['nomination_id'], ['book_nominations.id'],
            name='fk_nomination_votes_nomination_id_book_nominations', ondelete='CASCADE',
        ),
    )
    # Голоса клуба считаются одним запросом по club_id, а PK начинается с user_id
    # и как префикс его не покрывает. Индекс нужен и каскаду при удалении клуба.
    op.create_index('ix_nomination_votes_club_id', 'nomination_votes', ['club_id'])
    # FK не создаёт индекс на дочерней стороне - без него каскад при удалении
    # номинации сканирует таблицу целиком.
    op.create_index('ix_nomination_votes_nomination_id', 'nomination_votes', ['nomination_id'])


def downgrade() -> None:
    op.drop_table('nomination_votes')
    op.drop_table('book_nominations')
