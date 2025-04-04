from fastapi import HTTPException

from app.core.errors.errors import UnprocessableEntity, Conflict, NotFound
from app.db.models.db_user import DBUser
from app.db.repositories.user_repository import UserRepository
from app.schemas.public_user_schema import PublicUserResponseModel, UpdateUserRequestModel


class UserService:
    user_repository: UserRepository

    def __init__(self) -> None:
        self.user_repository = UserRepository()

    def get_current_user(self, access_token: str) -> PublicUserResponseModel:
        db_user: DBUser = self.user_repository.get_user_by_access_token(access_token)

        return PublicUserResponseModel(**db_user.to_dict())

    def get_user_by_id(self, user_id: int) -> PublicUserResponseModel:
        db_user: DBUser = self.user_repository.get_user_by_id(user_id)

        if db_user is None:
            raise NotFound(errors=["Пользователь с таким id не найден"])

        return PublicUserResponseModel(**db_user.to_dict())

    def update_user_info(self, access_token: str, model: UpdateUserRequestModel) -> PublicUserResponseModel:
        self.validate_phone_number(model.phone_number)
        db_user: DBUser = self.user_repository.update_user_info(access_token, model.name, model.phone_number)

        return PublicUserResponseModel(**db_user.to_dict())

    def validate_phone_number(self, phone_number: int):
        phone_str = str(phone_number)

        if not phone_str.isdigit():
            raise UnprocessableEntity(errors=["Номер должен содержать только цифры"])

        if len(phone_str) < 10 or len(phone_str) > 15:
            raise UnprocessableEntity(errors=["Номер телефона должен быть от 10 до 15 символов"])

        if self.__is_unique_phone_number(phone_number) is False:
            raise Conflict(errors=["Пользователь с таким номером телефона уже зарегистрирован"])

    def __is_unique_phone_number(self, phone_number: int) -> bool:
        user = self.user_repository.get_user_by_phone_number(phone_number)

        if user:
            return False
        else:
            return True