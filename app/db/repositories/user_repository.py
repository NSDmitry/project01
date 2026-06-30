import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.db_user import DBUser
from app.core.errors.errors import NotFound, Conflict, InternalServerError


class UserRepository:
    db: AsyncSession

    logger = logging.getLogger(__name__)

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_id(self, user_id: int) -> DBUser:
        result = await self.db.execute(select(DBUser).where(DBUser.id == user_id))
        db_user = result.scalar_one_or_none()

        if db_user is None:
            raise NotFound(errors=["Пользователь с таким id не найден"])

        return db_user

    async def get_user_by_phone_number(self, phone_number: int) -> DBUser:
        result = await self.db.execute(select(DBUser).where(DBUser.phone_number == phone_number))

        return result.scalar_one_or_none()

    async def create_user(self, name: str, phone_number: int, password: str) -> DBUser:
        user_db_model = DBUser()
        user_db_model.name = name
        user_db_model.phone_number = phone_number
        user_db_model.password = password

        if self.db is None:
            raise InternalServerError(errors=["Соединение с базой данных не установлено."])

        try:
            self.db.add(user_db_model)
            await self.db.commit()
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

    async def get_user_by_telegram_id(self, telegram_id: int) -> DBUser:
        result = await self.db.execute(select(DBUser).where(DBUser.telegram_id == telegram_id))

        return result.scalar_one_or_none()

    async def create_user_by_telegram(self, telegram_id: int, password: str, name: str) -> DBUser:
        user_db_model = DBUser()
        user_db_model.name = name
        user_db_model.password = password
        user_db_model.telegram_id = telegram_id
        user_db_model.is_telegram_user = True

        try:
            self.db.add(user_db_model)
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            self.logger.error(f"IntegrityError: {str(e)}")
            raise Conflict(errors=["Пользователь с таким Telegram ID уже зарегистрирован."])

        await self.db.refresh(user_db_model)

        return user_db_model

    async def update_user_info(self, user_id: int, name: str, phone_number: str) -> DBUser:
        db_user = await self.get_user_by_id(user_id)

        db_user.name = name
        db_user.phone_number = phone_number

        await self.db.commit()
        await self.db.refresh(db_user)

        return db_user

    async def update_user_password(self, user_id: int, password: str) -> DBUser:
        db_user = await self.get_user_by_id(user_id)
        db_user.password = password

        await self.db.commit()
        await self.db.refresh(db_user)

        return db_user
