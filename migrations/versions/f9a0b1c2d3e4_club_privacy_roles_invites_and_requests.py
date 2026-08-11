"""club privacy, member roles, invites and join requests

Приватность клуба: как в него попасть - свободно (public), по одобренной заявке
(by_request) или по коду приглашения (by_invite). На видимость клуба в каталоге и
поиске режим не влияет: клуб «по заявке» иначе нельзя было бы найти, чтобы подать
заявку. Значения держит CHECK, а не enum-тип Postgres - добавить значение потом
дешевле.

club_members.role - moderator или member. Владельца здесь нет: владение хранит
book_clubs.owner_id, и дублировать его ролью значило бы завести второй источник
правды. Существующие участники получают member через server_default.

club_invites.code уникален глобально - по нему вступают, не зная id клуба.
created_by без FK: пользователи в другом домене, а уход создателя приглашение не
отзывает. expires_at NULL - код бессрочный.

club_join_requests - одна строка на пару (клуб, пользователь): повторная подача
переписывает статус, а не плодит заявки. user_id без FK, строки чистит код при
удалении пользователя; индекс по user_id - для этой чистки.

Revision ID: f9a0b1c2d3e4
Revises: d7e8f9a0b1c2
Create Date: 2026-08-10 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'book_clubs',
        sa.Column('privacy', sa.String(), server_default='public', nullable=False),
    )
    op.create_check_constraint(
        'ck_book_clubs_privacy', 'book_clubs', "privacy IN ('public', 'by_request', 'by_invite')"
    )

    op.add_column(
        'club_members',
        sa.Column('role', sa.String(), server_default='member', nullable=False),
    )
    op.create_check_constraint(
        'ck_club_members_role', 'club_members', "role IN ('member', 'moderator')"
    )

    op.create_table(
        'club_invites',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('club_id', sa.BigInteger(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('created_by', sa.BigInteger(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_club_invites_code'),
        sa.ForeignKeyConstraint(
            ['club_id'], ['book_clubs.id'], name='fk_club_invites_club_id_book_clubs', ondelete='CASCADE'
        ),
    )
    op.create_index('ix_club_invites_club_id', 'club_invites', ['club_id'])

    op.create_table(
        'club_join_requests',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('club_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(), server_default='pending', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', 'user_id', name='uq_club_join_requests_club_id_user_id'),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name='ck_club_join_requests_status'
        ),
        sa.ForeignKeyConstraint(
            ['club_id'], ['book_clubs.id'], name='fk_club_join_requests_club_id_book_clubs', ondelete='CASCADE'
        ),
    )
    op.create_index('ix_club_join_requests_user_id', 'club_join_requests', ['user_id'])


def downgrade() -> None:
    op.drop_table('club_join_requests')
    op.drop_table('club_invites')

    op.drop_constraint('ck_club_members_role', 'club_members', type_='check')
    op.drop_column('club_members', 'role')

    op.drop_constraint('ck_book_clubs_privacy', 'book_clubs', type_='check')
    op.drop_column('book_clubs', 'privacy')
