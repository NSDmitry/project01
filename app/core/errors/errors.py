from app.core.errors.APIExeption import APIException
from fastapi import status


class BadRequest(APIException):
    def __init__(self, message="Неверный запрос", errors=None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, errors)


class Unauthorized(APIException):
    def __init__(self, message="Не авторизован", errors=None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, errors)


class Forbidden(APIException):
    def __init__(self, message="Доступ запрещён", errors=None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, errors)


class NotFound(APIException):
    def __init__(self, message="Не найдено", errors=None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, errors)


class Conflict(APIException):
    def __init__(self, message="Конфликт", errors=None):
        super().__init__(message, status.HTTP_409_CONFLICT, errors)


class UnprocessableEntity(APIException):
    def __init__(self, message="Невозможно обработать запрос", errors=None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, errors)


class InternalServerError(APIException):
    def __init__(self, message="Внутренняя ошибка сервера", errors=None):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, errors)