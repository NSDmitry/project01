from app.core.errors.errors import UnprocessableEntity, Conflict, NotFound
from app.core.models.response_model import ResponseModel
from app.db.models.db_user import DBUser
from app.db.repositories.user_repository import UserRepository
from app.schemas.public_user_schema import PublicUserResponseModel, UpdateUserRequestModel


class UserService:
    user_repository: UserRepository

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def get_user_by_id(self, user_id: int) -> PublicUserResponseModel:
        db_user: DBUser = self.user_repository.get_user_by_id(user_id)

        if db_user is None:
            raise NotFound(errors=["Пользователь с таким id не найден"])

        return ResponseModel.success_response(PublicUserResponseModel(**db_user.to_dict()))

    def update_user_info(self, user: DBUser, model: UpdateUserRequestModel) -> PublicUserResponseModel:
        self.validate_phone_number(model.phone_number, exclude_user_id=user.id)
        updated_user: DBUser = self.user_repository.update_user_info(user.id, model.name, model.phone_number)

        return ResponseModel.success_response(PublicUserResponseModel(**updated_user.to_dict()))

    def validate_phone_number(self, phone_number: int, exclude_user_id: int | None = None):
        phone_str = str(phone_number)

        if phone_number is None:
            raise UnprocessableEntity(errors=["Номер телефона не может быть пустым"])

        if not phone_str.isdigit():
            raise UnprocessableEntity(errors=["Номер должен содержать только цифры"])

        if len(phone_str) < 10 or len(phone_str) > 15:
            raise UnprocessableEntity(errors=["Номер телефона должен быть от 10 до 15 символов"])

        if not self.__is_unique_phone_number(phone_number, exclude_user_id=exclude_user_id):
            raise Conflict(errors=["Пользователь с таким номером телефона уже зарегистрирован"])

    def __is_unique_phone_number(self, phone_number: int, exclude_user_id: int | None = None) -> bool:
        user = self.user_repository.get_user_by_phone_number(phone_number)

        if user and user.id != exclude_user_id:
            return False
        else:
            return True
