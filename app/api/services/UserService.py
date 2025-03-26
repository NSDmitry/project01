from fastapi import HTTPException

from app.db.models.DBUser import DBUser
from app.db.repositories.UserRepository import UserRepository
from app.schemas.public_user_schema import PublicUserResponseModel, UpdateUserRequestModel


class UserService:
    user_repository: UserRepository

    def __init__(self) -> None:
        self.user_repository = UserRepository()

    def get_current_user(self, access_token: str) -> PublicUserResponseModel:
        db_user: DBUser = self.user_repository.get_user_by_access_token(access_token)

        return PublicUserResponseModel.from_db_model(db_model=db_user)

    def get_user_by_id(self, user_id: int) -> PublicUserResponseModel:
        db_user: DBUser = self.user_repository.get_user_by_id(user_id)

        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь с таким id не найден")

        return PublicUserResponseModel.from_db_model(db_model=db_user)

    def update_user_info(self, access_token: str, model: UpdateUserRequestModel) -> PublicUserResponseModel:
        self.validate_phone_number(model.phone_number)
        db_user: DBUser = self.user_repository.update_user_info(access_token, model.name, model.phone_number)

        return PublicUserResponseModel.from_db_model(db_user)

    def validate_phone_number(self, phone_number: int):
        phone_str = str(phone_number)

        if not phone_str.isdigit():
            raise HTTPException(status_code=400, detail="Номер должен содержать только символы")

        if len(phone_str) < 10 or len(phone_str) > 15:
            raise HTTPException(status_code=400, detail="Номер телефона должен быть от 10 до 15 символов")

        if self.__is_unique_phone_number(phone_number) is False:
            raise HTTPException(status_code=409, detail="Пользователь с таким номером телефона уже зарегистрирован")

    def __is_unique_phone_number(self, phone_number: int) -> bool:
        user = self.user_repository.get_user_by_phone_number(phone_number)

        if user:
            return False
        else:
            return True