from sqlalchemy import Column, Integer, Table, ForeignKey

from database import Base

# Промежуточная таблица для связи many-to-many
user_bookclub = Table(
    'user_bookclub',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('bookclub_id', Integer, ForeignKey('book_clubs.id'))
)