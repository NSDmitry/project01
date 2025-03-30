from typing import Generic, TypeVar, Optional, List

from pydantic import Field
from pydantic.generics import GenericModel

T = TypeVar('T')


class ResponseModel(GenericModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    errors: List[str] = Field(default_factory=list)

    @classmethod
    def success_response(cls, data: Optional[T] = None, message: str = "Операция выполнена успешно") -> "ResponseModel[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_response(cls, message: str = "Произошла ошибка", errors: Optional[List[str]] = None) -> "ResponseModel[None]":
        return cls(success=False, message=message, errors=errors or [])

    def to_dict(self) -> dict:
        return self.dict()

    def to_json(self, **kwargs) -> str:
        return self.json(**kwargs)