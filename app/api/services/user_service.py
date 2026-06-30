from app.core.errors.errors import Conflict, NotFound
from app.core.models.response_model import ResponseModel
from app.db.models.db_user import DBUser
from app.db.repositories.user_repository import UserRepository
from app.schemas.public_user_schema import PublicUserResponseModel, UpdateUserRequestModel


class UserService:
    user_repository: UserRepository

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_user_by_id(self, user_id: int) -> PublicUserResponseModel:
        db_user: DBUser = await self.user_repository.get_user_by_id(user_id)

        if db_user is None:
            raise NotFound(errors=["Пользователь с таким id не найден"])

        return ResponseModel.ok(PublicUserResponseModel.model_validate(db_user))

    async def update_user_info(self, user: DBUser, model: UpdateUserRequestModel) -> PublicUserResponseModel:
        await self.validate_phone_number(model.phone_number, exclude_user_id=user.id)
        updated_user: DBUser = await self.user_repository.update_user_info(user.id, model.name, model.phone_number)

        return ResponseModel.ok(PublicUserResponseModel.model_validate(updated_user))

    async def validate_phone_number(self, phone_number: str, exclude_user_id: int | None = None):
        if not await self.__is_unique_phone_number(phone_number, exclude_user_id=exclude_user_id):
            raise Conflict(errors=["Пользователь с таким номером телефона уже зарегистрирован"])

    async def __is_unique_phone_number(self, phone_number: str, exclude_user_id: int | None = None) -> bool:
        user = await self.user_repository.get_user_by_phone_number(phone_number)

        if user and user.id != exclude_user_id:
            return False
        else:
            return True
