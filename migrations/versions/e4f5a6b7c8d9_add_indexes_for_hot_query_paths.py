"""add indexes for hot query paths

До этой ревизии в схеме не было ни одного явного индекса - только те, что БД
создаёт под PRIMARY KEY и UNIQUE. Все остальные фильтры шли Seq Scan'ом.

Что закрывается:

  * user_sessions.sid_hash - поиск сессии на каждом авторизованном запросе;
  * threads(club_id, created_at, id) и comments(thread_id, created_at, id) -
    лента клуба и комментарии треда: фильтр и сортировка одним индексом,
    узел Sort из плана уходит;
  * club_members.user_id и comment_likes.user_id - составные ключи этих таблиц
    (club_id, user_id) и (comment_id, user_id) обслуживают только выборку по
    первой колонке, поиск по user_id шёл полным сканом;
  * book_clubs.owner_id, threads.author_id, comments.author_id - удаление
    пользователя: FK между доменами сняты, связи чистит код (handle_user_deleted);
  * threads.book_id - FK не создаёт индекс на дочерней стороне, поэтому
    удаление книги сканировало threads целиком ради ON DELETE SET NULL.

Колонки перечислены по возрастанию: btree читается в обе стороны (Index Scan
Backward), поэтому ASC-индекс обслуживает и ORDER BY ... DESC.

Индексы строятся CONCURRENTLY - обычный CREATE INDEX держит блокировку на запись
в таблицу всё время построения, а comments и comment_likes крупные. Поэтому
операции идут в autocommit_block: CONCURRENTLY не работает внутри транзакции.

Побочный эффект CONCURRENTLY: при сбое остаётся индекс в состоянии INVALID, и
повторный upgrade упадёт на конфликте имён. Тогда сначала убрать остаток -
DROP INDEX CONCURRENTLY <имя> - и запустить миграцию снова. IF NOT EXISTS здесь
намеренно не используется: он бы молча пропустил нерабочий индекс.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-10 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (имя, таблица, колонки, уникальный)
INDEXES: Sequence[tuple[str, str, list[str], bool]] = (
    ('ix_user_sessions_sid_hash', 'user_sessions', ['sid_hash'], True),
    ('ix_user_sessions_user_id_last_used', 'user_sessions', ['user_id', 'last_used'], False),
    ('ix_threads_club_id_created_at_id', 'threads', ['club_id', 'created_at', 'id'], False),
    ('ix_threads_author_id', 'threads', ['author_id'], False),
    ('ix_threads_book_id', 'threads', ['book_id'], False),
    ('ix_comments_thread_id_created_at_id', 'comments', ['thread_id', 'created_at', 'id'], False),
    ('ix_comments_author_id', 'comments', ['author_id'], False),
    ('ix_comment_likes_user_id', 'comment_likes', ['user_id'], False),
    ('ix_club_members_user_id', 'club_members', ['user_id'], False),
    ('ix_book_clubs_owner_id', 'book_clubs', ['owner_id'], False),
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, columns, unique in INDEXES:
            op.create_index(
                name, table, columns, unique=unique, postgresql_concurrently=True
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, _columns, _unique in reversed(INDEXES):
            op.drop_index(name, table_name=table, postgresql_concurrently=True)
