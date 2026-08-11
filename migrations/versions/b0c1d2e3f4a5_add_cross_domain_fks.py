"""cross-domain foreign keys

Кросс-доменные связи держались на голых id без FK - под распил на микросервисы,
чтобы таблицы доменов можно было развезти по разным базам. Распил отменён (#75):
целостность связей возвращается в БД. Каскады, которые раньше выполнял код по
событиям (user_deleted, clubs_deleted, genres_deleted), берёт на себя ON DELETE.

Правила удаления пользователя повторяют текущее поведение кода:
- CASCADE там, где строка без пользователя не имеет смысла (сессии, участие,
  заявки, голоса, прогресс, лайки);
- SET NULL там, где сущность переживает автора (клуб без владельца, анонимный
  тред/комментарий, приглашение - код выдан от имени клуба, а не создателя,
  поэтому created_by становится nullable).

threads.club_id - CASCADE: удаление клуба уносит треды силами БД (вместо
обработчика clubs_deleted). book_club_genres.genre_id - CASCADE (вместо
genres_deleted). threads.reading_stage_id - SET NULL: тред этапа переживает
удаление этапа как «тред про книгу в целом».

Перед констрейнтами чистятся осиротевшие строки (id в никуда) - иначе ALTER
TABLE упадёт на живой базе. Индексы на дочерней стороне под каждый каскад уже
есть; недостаёт только club_invites.created_by - добавляется здесь.

Revision ID: b0c1d2e3f4a5
Revises: a1b2c3d4e5f7
Create Date: 2026-08-11 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0c1d2e3f4a5'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (таблица, колонка, родитель, ondelete). Имя констрейнта строится по
# соглашению fk_<таблица>_<колонка>_<родитель>.
FKS = [
    ('user_sessions', 'user_id', 'users', 'CASCADE'),
    ('book_clubs', 'owner_id', 'users', 'SET NULL'),
    ('club_members', 'user_id', 'users', 'CASCADE'),
    ('club_join_requests', 'user_id', 'users', 'CASCADE'),
    ('club_invites', 'created_by', 'users', 'SET NULL'),
    ('nomination_votes', 'user_id', 'users', 'CASCADE'),
    ('reading_progress', 'user_id', 'users', 'CASCADE'),
    ('threads', 'author_id', 'users', 'SET NULL'),
    ('comments', 'author_id', 'users', 'SET NULL'),
    ('comment_likes', 'user_id', 'users', 'CASCADE'),
    ('threads', 'club_id', 'book_clubs', 'CASCADE'),
    ('book_club_genres', 'genre_id', 'genres', 'CASCADE'),
    ('threads', 'reading_stage_id', 'reading_stages', 'SET NULL'),
]


def upgrade() -> None:
    # Осиротевшие строки: NOT NULL-ссылки в никуда удаляются, nullable - обнуляются.
    # Треды несуществующих клубов - первыми: их комментарии и лайки уносят уже
    # существующие внутридоменные каскады comments.thread_id и comment_likes.comment_id.
    op.execute(
        "DELETE FROM threads t WHERE NOT EXISTS "
        "(SELECT 1 FROM book_clubs c WHERE c.id = t.club_id)"
    )
    for table, column in [
        ('user_sessions', 'user_id'),
        ('club_members', 'user_id'),
        ('club_join_requests', 'user_id'),
        ('nomination_votes', 'user_id'),
        ('reading_progress', 'user_id'),
        ('comment_likes', 'user_id'),
    ]:
        op.execute(
            f"DELETE FROM {table} t WHERE NOT EXISTS "
            f"(SELECT 1 FROM users u WHERE u.id = t.{column})"
        )
    for table, column in [
        ('book_clubs', 'owner_id'),
        ('threads', 'author_id'),
        ('comments', 'author_id'),
    ]:
        op.execute(
            f"UPDATE {table} t SET {column} = NULL WHERE {column} IS NOT NULL "
            f"AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = t.{column})"
        )
    op.execute(
        "DELETE FROM book_club_genres t WHERE NOT EXISTS "
        "(SELECT 1 FROM genres g WHERE g.id = t.genre_id)"
    )
    op.execute(
        "UPDATE threads t SET reading_stage_id = NULL WHERE reading_stage_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM reading_stages s WHERE s.id = t.reading_stage_id)"
    )

    # created_by переживает создателя (SET NULL) - колонка становится nullable,
    # осиротевшие значения обнуляются до констрейнта.
    op.alter_column('club_invites', 'created_by', existing_type=sa.BigInteger(), nullable=True)
    op.execute(
        "UPDATE club_invites t SET created_by = NULL WHERE created_by IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = t.created_by)"
    )
    # Под SET NULL при удалении пользователя: без индекса он сканирует приглашения целиком.
    op.create_index('ix_club_invites_created_by', 'club_invites', ['created_by'])

    for table, column, parent, ondelete in FKS:
        op.create_foreign_key(
            f'fk_{table}_{column}_{parent}', table, parent, [column], ['id'], ondelete=ondelete
        )


def downgrade() -> None:
    for table, column, parent, _ in reversed(FKS):
        op.drop_constraint(f'fk_{table}_{column}_{parent}', table, type_='foreignkey')
    op.drop_index('ix_club_invites_created_by', table_name='club_invites')
    # До миграции NULL в created_by быть не могло - строки с ним при откате удаляются.
    op.execute("DELETE FROM club_invites WHERE created_by IS NULL")
    op.alter_column('club_invites', 'created_by', existing_type=sa.BigInteger(), nullable=False)
