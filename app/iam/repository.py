import logging

from sqlalchemy import DateTime, or_, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.models import BookClub
from app.core.errors.errors import NotFound, Conflict, InternalServerError
from app.discussions.models import Comment, Thread
from app.iam.models import User, UserSession


class UserRepository:
    db: AsyncSession

    logger = logging.getLogger(__name__)

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_id(self, user_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()

        if db_user is None:
            raise NotFound(errors=["Пользователь с таким id не найден"])

        return db_user

    async def get_user_by_phone_number(self, phone_number: str) -> User:
        result = await self.db.execute(select(User).where(User.phone_number == phone_number))

        return result.scalar_one_or_none()

    async def get_user_by_telegram_id(self, telegram_id: int) -> User:
        result = await self.db.execute(select(User).where(User.telegram_id == telegram_id))

        return result.scalar_one_or_none()

    async def create_telegram_user(self, telegram_id: int, name: str) -> User:
        user_db_model = User()
        user_db_model.name = name
        user_db_model.telegram_id = telegram_id

        try:
            self.db.add(user_db_model)
            await self.db.flush()
        except IntegrityError:
            # Параллельный первый вход уже создал запись - используем существующую.
            await self.db.rollback()
            return await self.get_user_by_telegram_id(telegram_id)

        await self.db.refresh(user_db_model)

        return user_db_model

    async def create_user(self, name: str, phone_number: str, password: str) -> User:
        user_db_model = User()
        user_db_model.name = name
        user_db_model.phone_number = phone_number
        user_db_model.password = password

        try:
            self.db.add(user_db_model)
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            self.logger.error(f"IntegrityError: {str(e)}")  # Логируем ошибку
            raise Conflict(errors=["Пользователь с таким номером телефона уже зарегистрирован."])
        except Exception as e:
            self.logger.error(f"Exception: {str(e)}")  # Логируем ошибку
            await self.db.rollback()
            raise InternalServerError(errors=["Ошибка при создании пользователя."])

        await self.db.refresh(user_db_model)

        return user_db_model

    async def update_user_info(self, user_id: int, name: str, phone_number: str) -> User:
        db_user = await self.get_user_by_id(user_id)

        db_user.name = name
        db_user.phone_number = phone_number

        try:
            await self.db.flush()
        except IntegrityError:
            # Гонка: номер заняли между проверкой уникальности и flush.
            await self.db.rollback()
            raise Conflict(errors=["Пользователь с таким номером телефона уже зарегистрирован"])

        await self.db.refresh(db_user)

        return db_user

    async def update_user_password(self, user_id: int, password: str) -> User:
        db_user = await self.get_user_by_id(user_id)
        db_user.password = password

        await self.db.flush()
        await self.db.refresh(db_user)

        return db_user

    async def delete_user(
        self,
        user_id: int,
        delete_clubs: bool,
        delete_threads: bool,
        delete_comments: bool,
    ) -> None:
        # Клубы/треды/комменты висят на FK ON DELETE SET NULL - без явного удаления
        # они осиротеют (owner_id/author_id -> NULL). Флаг True удаляет контент до
        # пользователя; вложенное (треды, комменты, лайки) чистят каскады БД по
        # club_id/thread_id/comment_id.
        if delete_clubs:
            await self.db.execute(delete(BookClub).where(BookClub.owner_id == user_id))
        if delete_threads:
            await self.db.execute(delete(Thread).where(Thread.author_id == user_id))
        if delete_comments:
            await self.db.execute(delete(Comment).where(Comment.author_id == user_id))

        await self.db.execute(delete(User).where(User.id == user_id))
        await self.db.flush()


class UserSessionRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user_session(self, user_id: int, sid_hash: str, last_used: DateTime) -> UserSession:
        session = UserSession()
        session.user_id = user_id
        session.sid_hash = sid_hash
        session.last_used = last_used

        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        return session

    async def delete_sessions_over_limit(self, user_id: int, keep: int) -> None:
        newest = (
            select(UserSession.id)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.last_used.desc())
            .limit(keep)
        )
        await self.db.execute(
            delete(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.id.not_in(newest),
            )
        )
        await self.db.flush()

    async def delete_user_session(self, sid_hash: str):
        result = await self.db.execute(select(UserSession).where(UserSession.sid_hash == sid_hash))
        session = result.scalar_one_or_none()

        if session:
            await self.db.delete(session)
            await self.db.flush()

    async def get_user_session(self, sid_hash: str) -> UserSession:
        result = await self.db.execute(select(UserSession).where(UserSession.sid_hash == sid_hash))

        return result.scalar_one_or_none()

    async def update_last_used(self, session: UserSession, last_used: DateTime) -> UserSession:
        session.last_used = last_used
        await self.db.flush()

        return session

    async def delete_all_user_sessions(self, user_id: int):
        await self.db.execute(delete(UserSession).where(UserSession.user_id == user_id))
        await self.db.flush()

    async def delete_idle_sessions(self, cutoff: DateTime) -> int:
        result = await self.db.execute(
            delete(UserSession).where(
                or_(
                    UserSession.last_used.is_(None),
                    UserSession.last_used < cutoff,
                )
            )
        )
        await self.db.flush()

        return result.rowcount
