from app.core.errors.APIException import APIException
from fastapi import status


class BadRequest(APIException):
    def __init__(self, message: str = "Неверный запрос", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST, errors)


class Unauthorized(APIException):
    def __init__(self, message: str = "Не авторизован", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, errors)


class Forbidden(APIException):
    def __init__(self, message: str = "Доступ запрещён", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN, errors)


class NotFound(APIException):
    def __init__(self, message: str = "Не найдено", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_404_NOT_FOUND, errors)


class Conflict(APIException):
    def __init__(self, message: str = "Конфликт", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_409_CONFLICT, errors)


class TooManyRequests(APIException):
    def __init__(self, message: str = "Слишком много попыток", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS, errors)


class PayloadTooLarge(APIException):
    def __init__(self, message: str = "Файл слишком большой", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, errors)


class UnsupportedMediaType(APIException):
    def __init__(self, message: str = "Неподдерживаемый тип файла", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, errors)


class UnprocessableEntity(APIException):
    def __init__(self, message: str = "Невозможно обработать запрос", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, errors)


class InternalServerError(APIException):
    def __init__(self, message: str = "Внутренняя ошибка сервера", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, errors)


class ServiceUnavailable(APIException):
    def __init__(self, message: str = "Сервис временно недоступен", errors: list[str] | None = None) -> None:
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE, errors)