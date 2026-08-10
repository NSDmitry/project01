"""create readings, reading_stages, reading_progress and threads.reading_stage_id

Совместное чтение: у клуба есть заход - книга, сроки и этапы (главы или страницы
с датами), а участники отмечают по нему свой прогресс.

readings.club_id - CASCADE: заходы живут ровно столько, сколько клуб. book_id -
SET NULL, как у threads.book_id: удаление книги не должно уносить историю чтения.
Незакрытый заход у клуба ровно один - это держит частичный уникальный индекс по
club_id, а не проверка в коде: два параллельных создания иначе прошли бы оба.

reading_progress.user_id - без FK: пользователи в другом домене, строки чистит код
при удалении пользователя и при выходе из клуба. stage_id - SET NULL: снятый этап
не должен уносить отметку участника.

threads.reading_stage_id - опциональная привязка обсуждения к этапу, без FK: треды
в другом домене и связаны с клубом только идентификатором. FK здесь ещё и вредил бы -
удаление клуба каскадом уносит этапы и в той же транзакции блокировало бы треды,
которые чистит обработчик CLUBS_DELETED в своей сессии.

Revision ID: c6d7e8f9a0b1
Revises: e8f9a0b1c2d3
Create Date: 2026-08-10 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'readings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('club_id', sa.BigInteger(), nullable=False),
        sa.Column('book_id', sa.BigInteger(), nullable=True),
        sa.Column('started_at', sa.Date(), nullable=False),
        sa.Column('deadline', sa.Date(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['club_id'], ['book_clubs.id'], name='fk_readings_club_id_book_clubs', ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['book_id'], ['books.id'], name='fk_readings_book_id_books', ondelete='SET NULL'
        ),
    )
    op.create_index('ix_readings_club_id_id', 'readings', ['club_id', 'id'])
    op.create_index(
        'uq_readings_active_club_id',
        'readings',
        ['club_id'],
        unique=True,
        postgresql_where=sa.text('finished_at IS NULL'),
    )

    op.create_table(
        'reading_stages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('reading_id', sa.BigInteger(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('end_page', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reading_id', 'position', name='uq_reading_stages_reading_id_position'),
        sa.ForeignKeyConstraint(
            ['reading_id'], ['readings.id'], name='fk_reading_stages_reading_id_readings', ondelete='CASCADE'
        ),
    )

    op.create_table(
        'reading_progress',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('reading_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('stage_id', sa.BigInteger(), nullable=True),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reading_id', 'user_id', name='uq_reading_progress_reading_id_user_id'),
        sa.ForeignKeyConstraint(
            ['reading_id'], ['readings.id'], name='fk_reading_progress_reading_id_readings', ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['stage_id'], ['reading_stages.id'],
            name='fk_reading_progress_stage_id_reading_stages', ondelete='SET NULL',
        ),
    )
    op.create_index('ix_reading_progress_user_id', 'reading_progress', ['user_id'])
    op.create_index('ix_reading_progress_stage_id', 'reading_progress', ['stage_id'])

    op.add_column('threads', sa.Column('reading_stage_id', sa.BigInteger(), nullable=True))
    op.create_index('ix_threads_reading_stage_id', 'threads', ['reading_stage_id'])


def downgrade() -> None:
    op.drop_index('ix_threads_reading_stage_id', table_name='threads')
    op.drop_column('threads', 'reading_stage_id')

    op.drop_table('reading_progress')
    op.drop_table('reading_stages')
    op.drop_table('readings')
